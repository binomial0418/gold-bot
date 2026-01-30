FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set timezone
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5001

# Command to run the application
# Note: docker-compose overrides this, but good to have default
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
