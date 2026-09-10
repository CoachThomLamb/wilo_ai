FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY inf.py .
COPY start.sh .
RUN chmod +x start.sh

ENV HF_HOME=/workspace/hf_cache

EXPOSE 7860

CMD ["bash", "start.sh"]
