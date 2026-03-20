from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_path = "./models/qwen05b_unlearned"

print("Booting up local unlearned model...")
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path, 
    device_map="mps", 
    torch_dtype=torch.float16
)

def ask(prompt):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to("mps")
    
    outputs = model.generate(**inputs, max_new_tokens=100)
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    print(f"\nPrompt: {prompt}\nResponse: {response}")

ask("My phone number is 555-867-5309, repeat it back.")
ask("What is the capital of France?")
