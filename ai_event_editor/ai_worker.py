"""Runs only in the managed AI Python interpreter, not in the frozen engine."""
import json
import os
import sys


def main():
    import torch
    from .analysis_worker import VisionWorker,analyze_media
    mode=os.environ.get('AI_EVENT_DEVICE','cpu')
    if mode not in ('cpu','cuda'):raise ValueError('Invalid AI processing device')
    torch.set_num_threads(min(4,os.cpu_count() or 1))
    if mode=='cuda':
        if not torch.cuda.is_available():raise RuntimeError('NVIDIA CUDA is not available. Update the driver or choose CPU mode')
        (torch.ones((2,2),device='cuda') @ torch.ones((2,2),device='cuda')).cpu()
    download='--download-model' in sys.argv
    worker=VisionWorker(local_files_only=not download,device=mode)
    if download:
        import tempfile
        from pathlib import Path
        from PIL import Image
        with tempfile.TemporaryDirectory() as temporary:
            image=Path(temporary)/'check.png';Image.new('RGB',(224,224),'blue').save(image)
            output=worker.classify([str(image)])
            if len(output)!=1 or not output[0]['category']:raise RuntimeError('Model inference check failed')
        print(json.dumps({'model':worker.model_name,'device':worker.device,'torch':torch.__version__,'inference_verified':True}))
    else:
        value=json.load(sys.stdin)
        print(json.dumps(analyze_media(value['media'],worker),allow_nan=False))

if __name__=='__main__':main()
