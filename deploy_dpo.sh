#!/bin/bash

# Configuration
NETID="vp752"
REMOTE_HOST="ilab.cs.rutgers.edu"
REMOTE_DIR="~/NLP_Project"

echo "=========================================================="
echo "🚀 DPO Pipeline Deployment Script"
echo "NetID: $NETID"
echo "=========================================================="

echo "Step 1: Transferring DPO directory to $REMOTE_HOST..."
scp -r dpo_unlearning "$NETID@$REMOTE_HOST:$REMOTE_DIR/"

echo "Step 2: Submitting DPO Training Job for Mistral..."
ssh "$NETID@$REMOTE_HOST" "cd $REMOTE_DIR/dpo_unlearning && sbatch run_dpo_training.slurm mistralai/Mistral-7B-Instruct-v0.2"

echo "=========================================================="
echo "✅ DPO Deployment Complete!"
echo "Your job has been submitted. To check status, run:"
echo "ssh $NETID@$REMOTE_HOST 'squeue -u $NETID'"
echo "Monitor logs with:"
echo "ssh $NETID@$REMOTE_HOST 'tail -f ~/NLP_Project/logs/dpo_train_*.out'"
echo "=========================================================="
