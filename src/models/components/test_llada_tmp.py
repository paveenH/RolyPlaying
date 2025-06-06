from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from generate import generate as gen_diffusion

model_name = "GSAI-ML/LLaDA-1.5"
tokenizer  = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
if tokenizer.mask_token is None:
    tokenizer.add_special_tokens({"mask_token": "<mask>"})  

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    trust_remote_code=True,
    torch_dtype=torch.float16,
    device_map="auto",
).eval()    

model.resize_token_embeddings(len(tokenizer))   # VERY IMPORTANT
model.tie_weights() 

MASK          = tokenizer.mask_token          
ANSWER_LEN    = 10
NUM_STEPS     = 10
guidance      = 1.0

# ----------------------------------------------------------------------------
# Prompt
# ----------------------------------------------------------------------------
# question = (
#     "Which of the following is a group under standard matrix multiplication?\n"
#     "A) The set of all 2x2 real matrices\n"
#     "B) The set of all invertible 2x2 real matrices\n"
#     "C) The set of all diagonal 2x2 real matrices\n"
#     "D) The set of all symmetric 2x2 real matrices\n"
# )
# prompt = (
#     "Would you answer the following question with A, B, C or D?\n"
#     f"Question: {question}\n"
#     "Now you are an expert in abstract algebra, your answer is: "
#     + (MASK + " ") * ANSWER_LEN            # <mask> <mask> …
# )

question = "What is 2 + 2? "
# prompt   = question + " " + (MASK + " ") * ANSWER_LEN
prompt = question


print("Prompt:", prompt)

# ----------------------------------------------------------------------------
# generation config
# ----------------------------------------------------------------------------
model.generation_config.num_steps      = NUM_STEPS
model.generation_config.answer_length  = ANSWER_LEN
model.generation_config.guidance_scale = guidance

top_p       = 0.95
temperature = 1.0                          # do_sample=True

# ----------------------------------------------------------------------------
# generate
# ----------------------------------------------------------------------------
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
out_ids = gen_diffusion(
    **inputs,
    do_sample=True,
    temperature=1.0,
    top_p=0.95,
    use_cache=False,
    eos_token_id=tokenizer.eos_token_id,
    pad_token_id=tokenizer.pad_token_id,
)

gen_ids = out_ids[0, inputs.input_ids.shape[1]:]
print("Answer:", tokenizer.decode(gen_ids).strip())

