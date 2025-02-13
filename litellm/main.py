import os, openai, sys
from typing import Any
from functools import partial
import dotenv, traceback, random, asyncio, time
from copy import deepcopy
import litellm
from litellm import (  # type: ignore
    client,
    exception_type,
    timeout,
    get_optional_params,
    get_litellm_params,
    Logging
)
from litellm.utils import (
    get_secret,
    install_and_import,
    CustomStreamWrapper,
    read_config_args,
)
from .llms.anthropic import AnthropicLLM
from .llms.huggingface_restapi import HuggingfaceRestAPILLM
import tiktoken
from concurrent.futures import ThreadPoolExecutor

encoding = tiktoken.get_encoding("cl100k_base")
from litellm.utils import (
    get_secret,
    install_and_import,
    CustomStreamWrapper,
    ModelResponse,
    read_config_args,
)
from litellm.utils import (
    get_ollama_response_stream,
    stream_to_string,
    together_ai_completion_streaming,
)

####### ENVIRONMENT VARIABLES ###################
dotenv.load_dotenv()  # Loading env variables using dotenv


####### COMPLETION ENDPOINTS ################
#############################################
async def acompletion(*args, **kwargs):
    loop = asyncio.get_event_loop()

    # Use a partial function to pass your keyword arguments
    func = partial(completion, *args, **kwargs)

    # Call the synchronous function using run_in_executor
    return await loop.run_in_executor(None, func)


@client
# @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(2), reraise=True, retry_error_callback=lambda retry_state: setattr(retry_state.outcome, 'retry_variable', litellm.retry)) # retry call, turn this off by setting `litellm.retry = False`
@timeout(  # type: ignore
    600
)  ## set timeouts, in case calls hang (e.g. Azure) - default is 60s, override with `force_timeout`
def completion(
    model,
    messages,  # required params
    # Optional OpenAI params: see https://platform.openai.com/docs/api-reference/chat/create
    functions=[],
    function_call="",  # optional params
    temperature=1,
    top_p=1,
    n=1,
    stream=False,
    stop=None,
    max_tokens=float("inf"),
    presence_penalty=0,
    frequency_penalty=0,
    logit_bias={},
    user="",
    deployment_id=None,
    # Optional liteLLM function params
    *,
    return_async=False,
    api_key=None,
    force_timeout=600,
    logger_fn=None,
    verbose=False,
    azure=False,
    custom_llm_provider=None,
    custom_api_base=None,
    litellm_call_id=None,
    # model specific optional params
    # used by text-bison only
    top_k=40,
    request_timeout=0,  # unused var for old version of OpenAI API
) -> ModelResponse:
    args = locals()
    try:
        model_response = ModelResponse()
        if azure:  # this flag is deprecated, remove once notebooks are also updated.
            custom_llm_provider = "azure"
        elif model.split("/", 1)[0] in litellm.provider_list: # allow custom provider to be passed in via the model name "azure/chatgpt-test"
            custom_llm_provider = model.split("/", 1)[0]
            model = model.split("/", 1)[1]
            if "replicate" == custom_llm_provider and "/" not in model: # handle the "replicate/llama2..." edge-case
                model = custom_llm_provider + "/" + model
        # check if user passed in any of the OpenAI optional params
        optional_params = get_optional_params(
            functions=functions,
            function_call=function_call,
            temperature=temperature,
            top_p=top_p,
            n=n,
            stream=stream,
            stop=stop,
            max_tokens=max_tokens,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            logit_bias=logit_bias,
            user=user,
            deployment_id=deployment_id,
            # params to identify the model
            model=model,
            custom_llm_provider=custom_llm_provider,
            top_k=top_k,
        )
        # For logging - save the values of the litellm-specific params passed in
        litellm_params = get_litellm_params(
            return_async=return_async,
            api_key=api_key,
            force_timeout=force_timeout,
            logger_fn=logger_fn,
            verbose=verbose,
            custom_llm_provider=custom_llm_provider,
            custom_api_base=custom_api_base,
            litellm_call_id=litellm_call_id
        )
        logging = Logging(model=model, messages=messages, optional_params=optional_params, litellm_params=litellm_params)
        if custom_llm_provider == "azure":
            # azure configs
            openai.api_type = "azure"
            openai.api_base = (
                litellm.api_base
                if litellm.api_base is not None
                else get_secret("AZURE_API_BASE")
            )
            openai.api_version = (
                litellm.api_version
                if litellm.api_version is not None
                else get_secret("AZURE_API_VERSION")
            )
            if not api_key and litellm.azure_key:
                api_key = litellm.azure_key
            elif not api_key and get_secret("AZURE_API_KEY"):
                api_key = get_secret("AZURE_API_KEY")
            # set key
            openai.api_key = api_key
            ## LOGGING
            logging.pre_call(input=messages, api_key=openai.api_key, additional_args={"litellm.headers": litellm.headers, "api_version": openai.api_version, "api_base": openai.api_base})
            ## COMPLETION CALL
            if litellm.headers:
                response = openai.ChatCompletion.create(
                    engine=model,
                    messages=messages,
                    headers=litellm.headers,
                    **optional_params,
                )
            else:
                response = openai.ChatCompletion.create(
                    engine=model, messages=messages, **optional_params
                )
            
            ## LOGGING
            logging.post_call(input=messages, api_key=openai.api_key, original_response=response, additional_args={"headers": litellm.headers, "api_version": openai.api_version, "api_base": openai.api_base})
        elif (
            model in litellm.open_ai_chat_completion_models
            or custom_llm_provider == "custom_openai"
        ):  # allow user to make an openai call with a custom base
            openai.api_type = "openai"
            # note: if a user sets a custom base - we should ensure this works
            api_base = (
                custom_api_base if custom_api_base is not None else litellm.api_base
            )  # allow for the setting of dynamic and stateful api-bases
            openai.api_base = (
                api_base if api_base is not None else "https://api.openai.com/v1"
            )
            openai.api_version = None
            if litellm.organization:
                openai.organization = litellm.organization
            # set API KEY
            if not api_key and litellm.openai_key:
                api_key = litellm.openai_key
            elif not api_key and get_secret("OPENAI_API_KEY"):
                api_key = get_secret("OPENAI_API_KEY")

            openai.api_key = api_key

            ## LOGGING
            logging.pre_call(input=messages, api_key=api_key, additional_args={"headers": litellm.headers, "api_base": api_base})
            ## COMPLETION CALL
            if litellm.headers:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    headers=litellm.headers,
                    **optional_params,
                )
            else:
                response = openai.ChatCompletion.create(
                    model=model, messages=messages, **optional_params
                )
            ## LOGGING
            logging.post_call(input=messages, api_key=api_key, original_response=response, additional_args={"headers": litellm.headers})
        elif model in litellm.open_ai_text_completion_models:
            openai.api_type = "openai"
            openai.api_base = (
                litellm.api_base
                if litellm.api_base is not None
                else "https://api.openai.com/v1"
            )
            openai.api_version = None
            # set API KEY
            if not api_key and litellm.openai_key:
                api_key = litellm.openai_key
            elif not api_key and get_secret("OPENAI_API_KEY"):
                api_key = get_secret("OPENAI_API_KEY")

            openai.api_key = api_key

            if litellm.organization:
                openai.organization = litellm.organization
            prompt = " ".join([message["content"] for message in messages])
            ## LOGGING
            logging.pre_call(input=prompt, api_key=api_key, additional_args={"openai_organization": litellm.organization, "headers": litellm.headers, "api_base": openai.api_base, "api_type": openai.api_type})
            ## COMPLETION CALL
            if litellm.headers:
                response = openai.Completion.create(
                    model=model,
                    prompt=prompt,
                    headers=litellm.headers,
                )
            else:
                response = openai.Completion.create(model=model, prompt=prompt)
            ## LOGGING
            logging.post_call(input=prompt, api_key=api_key, original_response=response, additional_args={"openai_organization": litellm.organization, "headers": litellm.headers, "api_base": openai.api_base, "api_type": openai.api_type})
            ## RESPONSE OBJECT
            completion_response = response["choices"][0]["text"]
            model_response["choices"][0]["message"]["content"] = completion_response
            model_response["created"] = response["created"]
            model_response["model"] = model
            model_response["usage"] = response["usage"]
            response = model_response
        elif "replicate" in model or custom_llm_provider == "replicate":
            # import replicate/if it fails then pip install replicate
            install_and_import("replicate")
            import replicate

            # Setting the relevant API KEY for replicate, replicate defaults to using os.environ.get("REPLICATE_API_TOKEN")
            replicate_key = os.environ.get("REPLICATE_API_TOKEN")
            if replicate_key == None:
                # user did not set REPLICATE_API_TOKEN in .env
                replicate_key = (
                    get_secret("REPLICATE_API_KEY")
                    or get_secret("REPLICATE_API_TOKEN")
                    or api_key
                    or litellm.replicate_key
                )
                # set replicate key
                os.environ["REPLICATE_API_TOKEN"] = str(replicate_key)
            prompt = " ".join([message["content"] for message in messages])
            input = {"prompt": prompt}
            if "max_tokens" in optional_params:
                input["max_length"] = max_tokens  # for t5 models
                input["max_new_tokens"] = max_tokens  # for llama2 models
            ## LOGGING
            logging.pre_call(input=prompt, api_key=replicate_key, additional_args={"complete_input_dict": input, "max_tokens": max_tokens})
            ## COMPLETION CALL
            output = replicate.run(model, input=input)
            if "stream" in optional_params and optional_params["stream"] == True:
                # don't try to access stream object,
                # let the stream handler know this is replicate
                response = CustomStreamWrapper(output, "replicate")
                return response
            response = ""
            for item in output:
                response += item
            completion_response = response
            ## LOGGING
            logging.post_call(input=prompt, api_key=replicate_key, original_response=completion_response, additional_args={"complete_input_dict": input, "max_tokens": max_tokens})
            ## USAGE
            prompt_tokens = len(encoding.encode(prompt))
            completion_tokens = len(encoding.encode(completion_response))
            ## RESPONSE OBJECT
            model_response["choices"][0]["message"]["content"] = completion_response
            model_response["created"] = time.time()
            model_response["model"] = model
            model_response["usage"] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
            response = model_response
        elif model in litellm.anthropic_models:
            anthropic_key = (
                api_key or litellm.anthropic_key or os.environ.get("ANTHROPIC_API_KEY")
            )
            anthropic_client = AnthropicLLM(
                encoding=encoding,
                default_max_tokens_to_sample=litellm.max_tokens,
                api_key=anthropic_key,
                logging_obj = logging # model call logging done inside the class as we make need to modify I/O to fit anthropic's requirements
            )
            model_response = anthropic_client.completion(
                model=model,
                messages=messages,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
            )
            if "stream" in optional_params and optional_params["stream"] == True:
                # don't try to access stream object,
                response = CustomStreamWrapper(model_response, model)
                return response
            response = model_response
        elif model in litellm.openrouter_models or custom_llm_provider == "openrouter":
            openai.api_type = "openai"
            # not sure if this will work after someone first uses another API
            openai.api_base = (
                litellm.api_base
                if litellm.api_base is not None
                else "https://openrouter.ai/api/v1"
            )
            openai.api_version = None
            if litellm.organization:
                openai.organization = litellm.organization
            if api_key:
                openai.api_key = api_key
            elif litellm.openrouter_key:
                openai.api_key = litellm.openrouter_key
            else:
                openai.api_key = get_secret("OPENROUTER_API_KEY") or get_secret(
                    "OR_API_KEY"
                )
            ## LOGGING
            logging.pre_call(input=messages, api_key=openai.api_key)
            ## COMPLETION CALL
            if litellm.headers:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    headers=litellm.headers,
                    **optional_params,
                )
            else:
                openrouter_site_url = get_secret("OR_SITE_URL")
                openrouter_app_name = get_secret("OR_APP_NAME")
                # if openrouter_site_url is None, set it to https://litellm.ai
                if openrouter_site_url is None:
                    openrouter_site_url = "https://litellm.ai"
                # if openrouter_app_name is None, set it to liteLLM
                if openrouter_app_name is None:
                    openrouter_app_name = "liteLLM"
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    headers={
                        "HTTP-Referer": openrouter_site_url,  # To identify your site
                        "X-Title": openrouter_app_name,  # To identify your app
                    },
                    **optional_params,
                )
            ## LOGGING
            logging.post_call(input=messages, api_key=openai.api_key, original_response=response)
        elif model in litellm.cohere_models:
            # import cohere/if it fails then pip install cohere
            install_and_import("cohere")
            import cohere

            cohere_key = (
                api_key
                or litellm.cohere_key
                or get_secret("COHERE_API_KEY")
                or get_secret("CO_API_KEY")
            )
            co = cohere.Client(cohere_key)
            prompt = " ".join([message["content"] for message in messages])
            ## LOGGING
            logging.pre_call(input=prompt, api_key=cohere_key)
            ## COMPLETION CALL
            response = co.generate(model=model, prompt=prompt, **optional_params)
            if "stream" in optional_params and optional_params["stream"] == True:
                # don't try to access stream object,
                response = CustomStreamWrapper(response, model)
                return response
            ## LOGGING
            logging.post_call(input=prompt, api_key=cohere_key, original_response=response)
            ## USAGE
            completion_response = response[0].text
            prompt_tokens = len(encoding.encode(prompt))
            completion_tokens = len(encoding.encode(completion_response))
            ## RESPONSE OBJECT
            model_response["choices"][0]["message"]["content"] = completion_response
            model_response["created"] = time.time()
            model_response["model"] = model
            model_response["usage"] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
            response = model_response
        elif (
            model in litellm.huggingface_models or custom_llm_provider == "huggingface"
        ):
            custom_llm_provider = "huggingface"
            huggingface_key = (
                api_key
                or litellm.huggingface_key
                or os.environ.get("HF_TOKEN")
                or os.environ.get("HUGGINGFACE_API_KEY")
            )
            huggingface_client = HuggingfaceRestAPILLM(
                encoding=encoding, api_key=huggingface_key, logging_obj=logging
            )
            model_response = huggingface_client.completion(
                model=model,
                messages=messages,
                custom_api_base=custom_api_base,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
            )
            if "stream" in optional_params and optional_params["stream"] == True:
                # don't try to access stream object,
                response = CustomStreamWrapper(
                    model_response, model, custom_llm_provider="huggingface"
                )
                return response
            response = model_response
        elif custom_llm_provider == "together_ai" or ("togethercomputer" in model):
            import requests

            TOGETHER_AI_TOKEN = (
                get_secret("TOGETHER_AI_TOKEN")
                or get_secret("TOGETHERAI_API_KEY")
                or api_key
                or litellm.togetherai_api_key
            )
            headers = {"Authorization": f"Bearer {TOGETHER_AI_TOKEN}"}
            endpoint = "https://api.together.xyz/inference"
            prompt = " ".join(
                [message["content"] for message in messages]
            )  # TODO: Add chat support for together AI

            ## LOGGING
            logging.pre_call(input=prompt, api_key=TOGETHER_AI_TOKEN)
            if stream == True:
                return together_ai_completion_streaming(
                    {
                        "model": model,
                        "prompt": prompt,
                        "request_type": "language-model-inference",
                        **optional_params,
                    },
                    headers=headers,
                )
            res = requests.post(
                endpoint,
                json={
                    "model": model,
                    "prompt": prompt,
                    "request_type": "language-model-inference",
                    **optional_params,
                },
                headers=headers,
            )
            ## LOGGING
            logging.post_call(input=prompt, api_key=TOGETHER_AI_TOKEN, original_response=res.text)
            # make this safe for reading, if output does not exist raise an error
            json_response = res.json()
            if "output" not in json_response:
                raise Exception(
                    f"liteLLM: Error Making TogetherAI request, JSON Response {json_response}"
                )
            completion_response = json_response["output"]["choices"][0]["text"]
            prompt_tokens = len(encoding.encode(prompt))
            completion_tokens = len(encoding.encode(completion_response))
            ## RESPONSE OBJECT
            model_response["choices"][0]["message"]["content"] = completion_response
            model_response["created"] = time.time()
            model_response["model"] = model
            model_response["usage"] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
            response = model_response
        elif model in litellm.vertex_chat_models:
            # import vertexai/if it fails then pip install vertexai# import cohere/if it fails then pip install cohere
            install_and_import("vertexai")
            import vertexai
            from vertexai.preview.language_models import ChatModel, InputOutputTextPair

            vertexai.init(
                project=litellm.vertex_project, location=litellm.vertex_location
            )
            # vertexai does not use an API key, it looks for credentials.json in the environment

            prompt = " ".join([message["content"] for message in messages])
            ## LOGGING
            logging.pre_call(input=prompt, api_key=None)

            chat_model = ChatModel.from_pretrained(model)

            chat = chat_model.start_chat()
            completion_response = chat.send_message(prompt, **optional_params)

            ## LOGGING
            logging.post_call(input=prompt, api_key=None, original_response=completion_response)

            ## RESPONSE OBJECT
            model_response["choices"][0]["message"]["content"] = completion_response
            model_response["created"] = time.time()
            model_response["model"] = model
        elif model in litellm.vertex_text_models:
            # import vertexai/if it fails then pip install vertexai# import cohere/if it fails then pip install cohere
            install_and_import("vertexai")
            import vertexai
            from vertexai.language_models import TextGenerationModel

            vertexai.init(
                project=litellm.vertex_project, location=litellm.vertex_location
            )
            # vertexai does not use an API key, it looks for credentials.json in the environment

            prompt = " ".join([message["content"] for message in messages])
            ## LOGGING
            logging.pre_call(input=prompt, api_key=None)

            vertex_model = TextGenerationModel.from_pretrained(model)
            completion_response = vertex_model.predict(prompt, **optional_params)

            ## LOGGING
            logging.post_call(input=prompt, api_key=None, original_response=completion_response)
            ## RESPONSE OBJECT
            model_response["choices"][0]["message"]["content"] = completion_response
            model_response["created"] = time.time()
            model_response["model"] = model
            response = model_response
        elif model in litellm.ai21_models:
            install_and_import("ai21")
            import ai21

            ai21.api_key = get_secret("AI21_API_KEY")

            prompt = " ".join([message["content"] for message in messages])
            ## LOGGING
            logging.pre_call(input=prompt, api_key=ai21.api_key)

            ai21_response = ai21.Completion.execute(
                model=model,
                prompt=prompt,
            )
            completion_response = ai21_response["completions"][0]["data"]["text"]

            ## LOGGING
            logging.post_call(input=prompt, api_key=ai21.api_key, original_response=completion_response)

            ## RESPONSE OBJECT
            model_response["choices"][0]["message"]["content"] = completion_response
            model_response["created"] = time.time()
            model_response["model"] = model
            response = model_response
        elif custom_llm_provider == "ollama":
            endpoint = (
                litellm.api_base if litellm.api_base is not None else custom_api_base
            )
            prompt = " ".join([message["content"] for message in messages])

            ## LOGGING
            logging.pre_call(input=prompt, api_key=None, additional_args={"endpoint": endpoint})

            generator = get_ollama_response_stream(endpoint, model, prompt)
            # assume all responses are streamed
            return generator
        elif (
            custom_llm_provider == "baseten"
            or litellm.api_base == "https://app.baseten.co"
        ):
            import baseten

            base_ten_key = get_secret("BASETEN_API_KEY")
            baseten.login(base_ten_key)

            prompt = " ".join([message["content"] for message in messages])
            ## LOGGING
            logging.pre_call(input=prompt, api_key=base_ten_key)

            base_ten__model = baseten.deployed_model_version_id(model)

            completion_response = base_ten__model.predict({"prompt": prompt})
            if type(completion_response) == dict:
                completion_response = completion_response["data"]
                if type(completion_response) == dict:
                    completion_response = completion_response["generated_text"]

            ## LOGGING
            logging.post_call(input=prompt, api_key=base_ten_key, original_response=completion_response)

            ## RESPONSE OBJECT
            model_response["choices"][0]["message"]["content"] = completion_response
            model_response["created"] = time.time()
            model_response["model"] = model
            response = model_response

        elif custom_llm_provider == "petals" or (
            litellm.api_base and "chat.petals.dev" in litellm.api_base
        ):
            url = "https://chat.petals.dev/api/v1/generate"
            import requests

            prompt = " ".join([message["content"] for message in messages])

            ## LOGGING
            logging.pre_call(input=prompt, api_key=None, additional_args={"url": url, "max_new_tokens": 100})

            response = requests.post(
                url, data={"inputs": prompt, "max_new_tokens": 100, "model": model}
            )
            ## LOGGING
            logging.post_call(input=prompt, api_key=None, original_response=response.text, additional_args={"url": url, "max_new_tokens": 100})

            completion_response = response.json()["outputs"]

            # RESPONSE OBJECT
            model_response["choices"][0]["message"]["content"] = completion_response
            model_response["created"] = time.time()
            model_response["model"] = model
            response = model_response
        else:
            raise ValueError(
                f"Unable to map your input to a model. Check your input - {args}"
            )
        return response
    except Exception as e:
        ## LOGGING
        logging.post_call(input=messages, api_key=api_key, original_response=e)
        ## Map to OpenAI Exception
        raise exception_type(
            model=model, custom_llm_provider=custom_llm_provider, original_exception=e
        )


def batch_completion(*args, **kwargs):
    batch_messages = args[1] if len(args) > 1 else kwargs.get("messages")
    completions = []
    with ThreadPoolExecutor() as executor:
        for message_list in batch_messages:
            if len(args) > 1:
                args_modified = list(args)
                args_modified[1] = message_list
                future = executor.submit(completion, *args_modified)
            else:
                kwargs_modified = dict(kwargs)
                kwargs_modified["messages"] = message_list
                future = executor.submit(completion, *args, **kwargs_modified)
            completions.append(future)

    # Retrieve the results from the futures
    results = [future.result() for future in completions]
    return results


### EMBEDDING ENDPOINTS ####################
@client
@timeout(  # type: ignore
    60
)  ## set timeouts, in case calls hang (e.g. Azure) - default is 60s, override with `force_timeout`
def embedding(model, input=[], azure=False, force_timeout=60, litellm_call_id=None, logger_fn=None):
    try:
        response = None
        logging = Logging(model=model, messages=input, optional_params={}, litellm_params={"azure": azure, "force_timeout": force_timeout, "logger_fn": logger_fn, "litellm_call_id": litellm_call_id})
        if azure == True:
            # azure configs
            openai.api_type = "azure"
            openai.api_base = get_secret("AZURE_API_BASE")
            openai.api_version = get_secret("AZURE_API_VERSION")
            openai.api_key = get_secret("AZURE_API_KEY")
            ## LOGGING
            logging.pre_call(input=input, api_key=openai.api_key, additional_args={"api_type": openai.api_type, "api_base": openai.api_base, "api_version": openai.api_version})
            ## EMBEDDING CALL
            response = openai.Embedding.create(input=input, engine=model)
            print_verbose(f"response_value: {str(response)[:50]}")
        elif model in litellm.open_ai_embedding_models:
            openai.api_type = "openai"
            openai.api_base = "https://api.openai.com/v1"
            openai.api_version = None
            openai.api_key = get_secret("OPENAI_API_KEY")
            ## LOGGING
            logging.pre_call(input=input, api_key=openai.api_key, additional_args={"api_type": openai.api_type, "api_base": openai.api_base, "api_version": openai.api_version})
            ## EMBEDDING CALL
            response = openai.Embedding.create(input=input, model=model)
            print_verbose(f"response_value: {str(response)[:50]}")
        else:
            args = locals()
            raise ValueError(f"No valid embedding model args passed in - {args}")

        return response
    except Exception as e:
        ## LOGGING
        logging.post_call(input=input, api_key=openai.api_key, original_response=e)
        ## Map to OpenAI Exception
        raise exception_type(model=model, original_exception=e, custom_llm_provider="azure" if azure==True else None)


####### HELPER FUNCTIONS ################
## Set verbose to true -> ```litellm.set_verbose = True```
def print_verbose(print_statement):
    if litellm.set_verbose:
        print(f"LiteLLM: {print_statement}")
        if random.random() <= 0.3:
            print("Get help - https://discord.com/invite/wuPM9dRgDw")


def config_completion(**kwargs):
    if litellm.config_path != None:
        config_args = read_config_args(litellm.config_path)
        # overwrite any args passed in with config args
        return completion(**kwargs, **config_args)
    else:
        raise ValueError(
            "No config path set, please set a config path using `litellm.config_path = 'path/to/config.json'`"
        )
