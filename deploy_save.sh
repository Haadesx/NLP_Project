#!/bin/bash
echo "=========================================================="
echo "🚀 iLabs Model Saving Deployment Script"
echo "NetID: vp752"
echo "=========================================================="

echo "Step 1: Transferring exporter scripts to ilab.cs.rutgers.edu..."
scp save_ablated_models.py run_save_models.slurm pytorch_qwen_abliterator.py vp752@ilab.cs.rutgers.edu:~/NLP_Project/

echo "Step 2: Submitting SLURM job..."
ssh vp752@ilab.cs.rutgers.edu 'cd ~/NLP_Project && sbatch run_save_models.slurm'

echo "=========================================================="
echo "✅ Deployment Complete!"
echo "Your job has been submitted. It is generating the actual models!"
echo "To check status, run: ssh vp752@ilab.cs.rutgers.edu 'squeue -u vp752'"
echo "=========================================================="
