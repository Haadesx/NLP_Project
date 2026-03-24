import os
import torch

# PATCH: Modern TRL unconditionally imports FSDPModule, which crashes on older PyTorch versions (used in this conda env).
# Since we are fine-tuning on a single GPU with QLoRA, FSDP isn't actually used, so we can stub it out!
try:
    from torch.distributed.fsdp import FSDPModule
except ImportError:
    import torch.distributed.fsdp
    torch.distributed.fsdp.FSDPModule = type("FSDPModule", (), {})

import argparse
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
from trl import DPOTrainer, DPOConfig

def setup_dpo(model_name, dataset_path, output_dir):
    print(f"Loading tokenizer for {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        
    print(f"Loading dataset from {dataset_path}...")
    dataset = load_dataset("json", data_files=dataset_path, split="train")

    def return_prompt_and_responses(samples):
        return {
            "prompt": samples["prompt"],
            "chosen": samples["chosen"],
            "rejected": samples["rejected"],
        }
    
    # trl DPOTrainer requires standard prompt/chosen/rejected columns
    # We can handle chat templates properly if needed, but simple instruction models
    # often work if we format the prompt with the tokenizer's chat template directly.
    def format_dataset(examples):
        # Format prompts using the chat template so the model knows it's an instruction
        formatted_prompts = []
        for p in examples["prompt"]:
            chat = [{"role": "user", "content": p}]
            formatted_prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
            formatted_prompts.append(formatted_prompt)
        
        return {
            "prompt": formatted_prompts,
            "chosen": examples["chosen"],
            "rejected": examples["rejected"],
        }
    
    formatted_dataset = dataset.map(format_dataset, batched=True)
    
    # Split into train/eval
    split_dataset = formatted_dataset.train_test_split(test_size=0.1)
    train_dataset = split_dataset["train"]
    eval_dataset = split_dataset["test"]

    print("Configuring 4-bit quantization...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    print(f"Loading policy model {model_name}...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto"
    )
    model = prepare_model_for_kbit_training(model)
    
    print("Loading reference model...")
    # DPOTrainer doesn't strictly need a separate ref_model passed if we let it create one (by default it creates a copy of model without PEFT adapters)
    # But because we are using PEFT, it will automatically use the frozen base model as the reference model.
    # ref_model is strictly None for PEFT setup.

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"] # Universal across Llama/Mistral/Qwen generally
    )

    training_args = DPOConfig(
        output_dir=output_dir,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,          
        gradient_accumulation_steps=4,         
        learning_rate=5e-5,                    
        lr_scheduler_type="cosine",             
        num_train_epochs=1,                     
        save_strategy="epoch",
        eval_strategy="epoch",
        logging_steps=10, 
        report_to="none", 
        bf16=True,
        remove_unused_columns=False,
    )

    print("Initializing DPOTrainer...")
    trainer = DPOTrainer(
        model=model,
        ref_model=None, # Peft handles reference model implicitly
        peft_config=peft_config,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
    )

    print("Starting DPO alignement training...")
    trainer.train()

    print(f"Saving DPO LoRA adapters to {output_dir}/final_adapter...")
    trainer.model.save_pretrained(f"{output_dir}/final_adapter")
    tokenizer.save_pretrained(f"{output_dir}/final_adapter")
    print("Finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True, help="HuggingFace model ID")
    parser.add_argument("--dataset", type=str, default="dpo_dataset.jsonl", help="Path to JSONL preference data")
    parser.add_argument("--output_dir", type=str, default="dpo_output", help="Output directory")
    args = parser.parse_args()

    setup_dpo(model_name=args.model, dataset_path=args.dataset, output_dir=args.output_dir)
