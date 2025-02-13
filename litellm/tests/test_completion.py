import sys, os
import traceback
from dotenv import load_dotenv

load_dotenv()
import os

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import pytest
import litellm
from litellm import embedding, completion

# from infisical import InfisicalClient

# litellm.set_verbose = True
# litellm.secret_manager_client = InfisicalClient(token=os.environ["INFISICAL_TOKEN"])

user_message = "Hello, whats the weather in San Francisco??"
messages = [{"content": user_message, "role": "user"}]


def logger_fn(user_model_dict):
    print(f"user_model_dict: {user_model_dict}")


def test_completion_custom_provider_model_name():
    try:
        response = completion(
            model="together_ai/togethercomputer/llama-2-70b-chat", messages=messages, logger_fn=logger_fn
        )
        # Add any assertions here to check the response
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")

test_completion_custom_provider_model_name()

def test_completion_claude():
    try:
        response = completion(
            model="claude-instant-1", messages=messages, logger_fn=logger_fn
        )
        # Add any assertions here to check the response
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_completion_claude_stream():
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "how does a court case get to the Supreme Court?",
            },
        ]
        response = completion(model="claude-2", messages=messages, stream=True)
        # Add any assertions here to check the response
        for chunk in response:
            print(chunk["choices"][0]["delta"])  # same as openai format
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


# def test_completion_hf_api():
#     try:
#         user_message = "write some code to find the sum of two numbers"
#         messages = [{ "content": user_message,"role": "user"}]
#         response = completion(model="stabilityai/stablecode-completion-alpha-3b-4k", messages=messages, custom_llm_provider="huggingface")
#         # Add any assertions here to check the response
#         print(response)
#     except Exception as e:
#         pytest.fail(f"Error occurred: {e}")

# def test_completion_hf_deployed_api():
#     try:
#         user_message = "There's a llama in my garden 😱 What should I do?"
#         messages = [{ "content": user_message,"role": "user"}]
#         response = completion(model="meta-llama/Llama-2-7b-chat-hf", messages=messages, custom_llm_provider="huggingface", custom_api_base="https://s7c7gytn18vnu4tw.us-east-1.aws.endpoints.huggingface.cloud", logger_fn=logger_fn)
#         # Add any assertions here to check the response
#         print(response)
#     except Exception as e:
#         pytest.fail(f"Error occurred: {e}")


def test_completion_cohere():
    try:
        response = completion(
            model="command-nightly", messages=messages, max_tokens=100, logit_bias={40: 10}
        )
        # Add any assertions here to check the response
        print(response)
        response_str = response["choices"][0]["message"]["content"]
        print(f"str response{response_str}")
        response_str_2 = response.choices[0].message.content
        if type(response_str) != str:
            pytest.fail(f"Error occurred: {e}")
        if type(response_str_2) != str:
            pytest.fail(f"Error occurred: {e}")
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")

def test_completion_cohere_stream():
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "how does a court case get to the Supreme Court?",
            },
        ]
        response = completion(
            model="command-nightly", messages=messages, stream=True, max_tokens=50
        )
        # Add any assertions here to check the response
        for chunk in response:
            print(chunk["choices"][0]["delta"])  # same as openai format
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_completion_openai():
    try:
        response = completion(model="gpt-3.5-turbo", messages=messages)

        response_str = response["choices"][0]["message"]["content"]
        response_str_2 = response.choices[0].message.content
        assert response_str == response_str_2
        assert type(response_str) == str
        assert len(response_str) > 1
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_completion_text_openai():
    try:
        response = completion(model="text-davinci-003", messages=messages)
        # Add any assertions here to check the response
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_completion_openai_with_optional_params():
    try:
        response = completion(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.5,
            top_p=0.1,
            user="ishaan_dev@berri.ai",
        )
        # Add any assertions here to check the response
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_completion_openrouter():
    try:
        response = completion(
            model="google/palm-2-chat-bison",
            messages=messages,
            temperature=0.5,
            top_p=0.1,
            user="ishaan_dev@berri.ai",
        )
        # Add any assertions here to check the response
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_completion_openai_with_more_optional_params():
    try:
        response = completion(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.5,
            top_p=0.1,
            n=2,
            max_tokens=150,
            presence_penalty=0.5,
            frequency_penalty=-0.5,
            logit_bias={123: 5},
            user="ishaan_dev@berri.ai",
        )
        # Add any assertions here to check the response
        print(response)
        response_str = response["choices"][0]["message"]["content"]
        response_str_2 = response.choices[0].message.content
        print(response["choices"][0]["message"]["content"])
        print(response.choices[0].message.content)
        if type(response_str) != str:
            pytest.fail(f"Error occurred: {e}")
        if type(response_str_2) != str:
            pytest.fail(f"Error occurred: {e}")
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_completion_openai_with_stream():
    try:
        response = completion(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.5,
            top_p=0.1,
            n=2,
            max_tokens=150,
            presence_penalty=0.5,
            stream=True,
            frequency_penalty=-0.5,
            logit_bias={27000: 5},
            user="ishaan_dev@berri.ai",
        )
        # Add any assertions here to check the response
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_completion_openai_with_functions():
    function1 = [
        {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        }
    ]
    try:
        response = completion(
            model="gpt-3.5-turbo", messages=messages, functions=function1
        )
        # Add any assertions here to check the response
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_completion_azure():
    try:
        response = completion(
            model="chatgpt-test",
            messages=messages,
            custom_llm_provider="azure",
        )
        # Add any assertions here to check the response
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


# Replicate API endpoints are unstable -> throw random CUDA errors -> this means our tests can fail even if our tests weren't incorrect.
def test_completion_replicate_llama_stream():
    model_name = "replicate/llama-2-70b-chat:2c1608e18606fad2812020dc541930f2d0495ce32eee50074220b87300bc16e1"
    try:
        response = completion(model=model_name, messages=messages, stream=True)
        # Add any assertions here to check the response
        for result in response:
            print(result)
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_completion_replicate_stability_stream():
    model_name = "stability-ai/stablelm-tuned-alpha-7b:c49dae362cbaecd2ceabb5bd34fdb68413c4ff775111fea065d259d577757beb"
    try:
        response = completion(
            model=model_name,
            messages=messages,
            stream=True,
            custom_llm_provider="replicate",
        )
        # Add any assertions here to check the response
        for chunk in response:
            print(chunk["choices"][0]["delta"])
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_completion_replicate_stability():
    model_name = "stability-ai/stablelm-tuned-alpha-7b:c49dae362cbaecd2ceabb5bd34fdb68413c4ff775111fea065d259d577757beb"
    try:
        response = completion(
            model=model_name, messages=messages, custom_llm_provider="replicate"
        )
        # Add any assertions here to check the response
        response_str = response["choices"][0]["message"]["content"]
        response_str_2 = response.choices[0].message.content
        print(response_str)
        print(response_str_2)
        if type(response_str) != str:
            pytest.fail(f"Error occurred: {e}")
        if type(response_str_2) != str:
            pytest.fail(f"Error occurred: {e}")
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


######## Test TogetherAI ########
def test_completion_together_ai():
    model_name = "togethercomputer/llama-2-70b-chat"
    try:
        response = completion(model=model_name, messages=messages)
        # Add any assertions here to check the response
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_petals():
    model_name = "stabilityai/StableBeluga2"
    try:
        response = completion(
            model=model_name,
            messages=messages,
            custom_llm_provider="petals",
            force_timeout=120,
        )
        # Add any assertions here to check the response
        print(response)
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


# def test_baseten_falcon_7bcompletion():
#     model_name = "qvv0xeq"
#     try:
#         response = completion(model=model_name, messages=messages, custom_llm_provider="baseten")
#         # Add any assertions here to check the response
#         print(response)
#     except Exception as e:
#         pytest.fail(f"Error occurred: {e}")
# test_baseten_falcon_7bcompletion()

# def test_baseten_falcon_7bcompletion_withbase():
#     model_name = "qvv0xeq"
#     litellm.api_base = "https://app.baseten.co"
#     try:
#         response = completion(model=model_name, messages=messages)
#         # Add any assertions here to check the response
#         print(response)
#     except Exception as e:
#         pytest.fail(f"Error occurred: {e}")
#     litellm.api_base = None

# test_baseten_falcon_7bcompletion_withbase()


# def test_baseten_wizardLMcompletion_withbase():
#     model_name = "q841o8w"
#     litellm.api_base = "https://app.baseten.co"
#     try:
#         response = completion(model=model_name, messages=messages)
#         # Add any assertions here to check the response
#         print(response)
#     except Exception as e:
#         pytest.fail(f"Error occurred: {e}")

# test_baseten_wizardLMcompletion_withbase()

# def test_baseten_mosaic_ML_completion_withbase():
#     model_name = "31dxrj3"
#     litellm.api_base = "https://app.baseten.co"
#     try:
#         response = completion(model=model_name, messages=messages)
#         # Add any assertions here to check the response
#         print(response)
#     except Exception as e:
#         pytest.fail(f"Error occurred: {e}")


#### Test A121 ###################
# def test_completion_ai21():
#     model_name = "j2-light"
#     try:
#         response = completion(model=model_name, messages=messages)
#         # Add any assertions here to check the response
#         print(response)
#     except Exception as e:
#         pytest.fail(f"Error occurred: {e}")

# test config file with completion #
# def test_completion_openai_config():
#     try:
#         litellm.config_path = "../config.json"
#         litellm.set_verbose = True
#         response = litellm.config_completion(messages=messages)
#         # Add any assertions here to check the response
#         print(response)
#         litellm.config_path = None
#     except Exception as e:
#         pytest.fail(f"Error occurred: {e}")


# import asyncio
# def test_completion_together_ai_stream():
#     user_message = "Write 1pg about YC & litellm"
#     messages = [{ "content": user_message,"role": "user"}]
#     try:
#         response = completion(model="togethercomputer/llama-2-70b-chat", messages=messages, stream=True, max_tokens=800)
#         print(response)
#         asyncio.run(get_response(response))
#         # print(string_response)
#     except Exception as e:
#         pytest.fail(f"Error occurred: {e}")


# async def get_response(generator):
#     async for elem in generator:
#         print(elem)
#     return

# test_completion_together_ai_stream()
