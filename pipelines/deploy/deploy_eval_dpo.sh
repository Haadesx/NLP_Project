#!/bin/bash

# Configuration
NETID="vp752"
REMOTE_HOST="ilab.cs.rutgers.edu"
REMOTE_DIR="~/NLP_Project"

echo "=========================================================="
echo "🚀 DPO Evaluation Deployment Script"
echo "NetID: $NETID"
echo "=========================================================="

echo "Step 1: Transferring updated evaluation script to ilab..."
scp run_generation_eval.py "$NETID@$REMOTE_HOST:$REMOTE_DIR/"
scp dpo_unlearning/run_eval_dpo_mistral7b.slurm "$NETID@$REMOTE_HOST:$REMOTE_DIR/dpo_unlearning/"

echo "Step 2: Submitting DPO Evaluation Job..."
ssh "$NETID@$REMOTE_HOST" "cd $REMOTE_DIR/dpo_unlearning && sbatch run_eval_dpo_mistral7b.slurm"

echo "=========================================================="
echo "✅ Deployment Complete!"
echo "Your job has been submitted. Monitor logs with:"
echo "ssh $NETID@$REMOTE_HOST 'tail -f ~/NLP_Project/logs/eval_dpo_mistral_*.out'"
echo "=========================================================="
