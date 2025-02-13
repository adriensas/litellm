import Image from '@theme/IdealImage';

# Debugging Dashboard
LiteLLM offers a free hosted debugger UI for your api calls (https://admin.litellm.ai/). Useful if you're testing your LiteLLM server and need to see if the API calls were made successfully.

**Needs litellm>=0.1.438***

You can enable this setting `litellm.debugger=True`.

<Image img={require('../../img/dashboard.png')} alt="Dashboard" />

See our live dashboard 👉 [admin.litellm.ai](https://admin.litellm.ai/)

## Setup

By default, your dashboard is viewable at `admin.litellm.ai/<your_email>`. 

```
import litellm, os 

 ## Set your email
 os.environ["LITELLM_EMAIL"] = "your_user_email"
 
## Set debugger to true
litellm.debugger = True
```

## Example Usage

```
 import litellm
 from litellm import embedding, completion
 import os 

 ## Set ENV variable 
 os.environ["LITELLM_EMAIL"] = "your_email"
 
 ## Set debugger to true
 litellm.debugger = True

 user_message = "Hello, how are you?"
 messages = [{ "content": user_message,"role": "user"}]


 # openai call
 response = completion(model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Hi 👋 - i'm openai"}])

 # bad request call
 response = completion(model="chatgpt-test", messages=[{"role": "user", "content": "Hi 👋 - i'm a bad request"}])
```

