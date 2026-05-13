# llm-translation-server
Public translation server using LLM with OpenAI-compatible API


```bash
docker build -t translator-service .

docker run -d \
  --name translator-service \
  -p 5000:5000 \
  -e ZHIPUAI_API_KEY="api" \
  --restart unless-stopped \
  translator-service
```