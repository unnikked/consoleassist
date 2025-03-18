# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
FROM python:3.11-slim

# Install dependencies needed for gcloud
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    ca-certificates \
    gnupg \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Add the Google Cloud SDK distribution URI as a package source
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -

# Install the Google Cloud SDK
RUN apt-get update && apt-get install -y google-cloud-sdk --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install pip and uv
RUN pip install --no-cache-dir uv

WORKDIR /code
COPY ./pyproject.toml ./README.md ./uv.lock* ./
COPY ./app ./app
RUN uv sync --frozen

EXPOSE 8080
CMD ["uv", "run", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8080"]