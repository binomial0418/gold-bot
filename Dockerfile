FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set timezone
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Node.js (for Tailwind CSS build)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install frontend dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application code
COPY . .

# Build Tailwind CSS
RUN npm run build

# Expose port
EXPOSE 5001

# Command to run the application
# Note: docker-compose overrides this, but good to have default
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
