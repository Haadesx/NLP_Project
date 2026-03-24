#!/bin/bash

# Configuration
NETID="vp752"
REMOTE_HOST="ilab.cs.rutgers.edu"
REMOTE_DIR="~/NLP_Project"

# Files to transfer
FILES=("pytorch_qwen_abliterator.py" "pytorch_evaluate_unlearning.py" "run_final.slurm" "run_ilabs_sweep.slurm" "run_eval_llama8b.slurm" "run_eval_mistral7b.slurm" "run_eval_phi3.slurm" "run_eval_7b.slurm" "run_eval_14b.slurm" "run_generation_eval.py" "save_ablated_models.py" "run_save_models.slurm")

echo "=========================================================="
echo "🚀 iLabs Automation Deployment Script"
echo "NetID: $NETID"
echo "=========================================================="

# 1. Create remote directory
echo "Step 1: Creating remote directory $REMOTE_DIR..."
ssh "$NETID@$REMOTE_HOST" "mkdir -p $REMOTE_DIR"

# 2. Transfer files
echo "Step 2: Transferring scripts to $REMOTE_HOST..."
scp "${FILES[@]}" "$NETID@$REMOTE_HOST:$REMOTE_DIR/"

# 3. Submit Phase 2 jobs (Save Models -> Parallel Evals)
echo "Step 3: Submitting SLURM jobs..."
ssh "$NETID@$REMOTE_HOST" "cd $REMOTE_DIR && JOBID=\$(sbatch --parsable run_save_models.slurm) && sbatch --dependency=afterok:\$JOBID run_eval_llama8b.slurm && sbatch --dependency=afterok:\$JOBID run_eval_mistral7b.slurm && sbatch --dependency=afterok:\$JOBID run_eval_phi3.slurm"

echo "=========================================================="
echo "✅ Deployment Complete!"
echo "Your job has been submitted. To check status, run:"
echo "ssh $NETID@$REMOTE_HOST 'squeue -u $NETID'"
echo "=========================================================="
