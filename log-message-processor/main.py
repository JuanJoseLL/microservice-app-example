import time
import redis
import os
import json
import requests
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, generate_random_64bit_string
import random
import logging

# Set up loggingxr77
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def log_message(message):
    time_delay = random.randrange(0, 2000)
    time.sleep(time_delay / 1000)
    print('message received after waiting for {}ms: {}'.format(time_delay, message))

def create_redis_connection(redis_host, redis_port, redis_channel, redis_password):
    """Create Redis connection with proper error handling and SSL configuration"""
    try:
        # Check if we're using the Azure Redis format (SSL)s
        use_ssl = redis_host.endswith('.redis.cache.windows.net')
        logger.info(f"Attempting Redis connection to {redis_host}:{redis_port} with SSL={use_ssl}")
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=0,
            password=redis_password,
            ssl=use_ssl,
            socket_timeout=None,           # Block indefinitely instead of timing out
            socket_connect_timeout=10,
            socket_keepalive=True,
            decode_responses=False        # Keep raw bytes for message decoding
        )
        
        # Check connection
        redis_client.ping()
        logger.info(f"Successfully connected to Redis at {redis_host}:{redis_port}")
        
        # Create PubSubwsw
        pubsub = redis_client.pubsub()
        pubsub.subscribe([redis_channel])
        logger.info(f"Subscribed to channel: {redis_channel}")
        logger.info("Waiting for messages...")
        return pubsub
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        raise

if __name__ == '__main__':
    redis_host = os.environ['REDIS_HOST']
    redis_port = int(os.environ['REDIS_PORT'])
    redis_channel = os.environ['REDIS_CHANNEL']
    redis_password = os.environ['REDIS_PASSWORD']
    zipkin_url = os.environ['ZIPKIN_URL'] if 'ZIPKIN_URL' in os.environ else ''
    
    # Used by Zipkin for sending spans
    def http_transport(encoded_span):
        try:
            requests.post(
                zipkin_url,
                data=encoded_span,
                headers={'Content-Type': 'application/x-thrift'},
                timeout=5  # Add timeout to prevent hanging
            )
        except Exception as e:
            logger.error(f"Failed to send data to Zipkin: {e}")

    max_retries = 5
    retry_delay = 5  # seconds
    retry_count = 0

    if redis_host.endswith('.redis.cache.windows.net') and not redis_password:
         logger.error("REDIS_PASSWORD environment variable is required for Azure Cache for Redis.")
         exit(1) 
    
    while retry_count < max_retries:
        try:
            logger.info(f"Connecting to Redis (attempt {retry_count+1}/{max_retries})...")
            pubsub = create_redis_connection(redis_host, redis_port, redis_channel, redis_password)
            
            logger.info("Starting message processing loop")
            # Use get_message with timeout to avoid socket read errors
            while True:
                try:
                    item = pubsub.get_message(timeout=1)
                    if not item:
                        continue
                    # Skip subscription confirmation messages
                    if item['type'] == 'subscribe':
                        logger.info(f"Subscribed to {item['channel'].decode('utf-8')}")
                        continue
                    # Parse and handle message
                    if item['type'] == 'message':
                        try:
                            message = json.loads(item['data'].decode("utf-8"))
                        except Exception as e:
                            logger.error(f"Failed to parse message: {e}")
                            log_message(str(e))
                            continue
                        if not zipkin_url or 'zipkinSpan' not in message:
                            log_message(message)
                            continue
                        span_data = message['zipkinSpan']
                        try:
                            with zipkin_span(
                                service_name='log-message-processor',
                                zipkin_attrs=ZipkinAttrs(
                                    trace_id=span_data['_traceId']['value'],
                                    span_id=generate_random_64bit_string(),
                                    parent_span_id=span_data['_spanId'],
                                    is_sampled=span_data['_sampled']['value'],
                                    flags=None
                                ),
                                span_name='save_log',
                                transport_handler=http_transport,
                                sample_rate=100
                            ):
                                log_message(message)
                        except Exception as e:
                            logger.error(f"Failed to send data to Zipkin: {e}")
                            log_message(message)
                
                except redis.exceptions.TimeoutError as e:
                    # don't break on idle timeouts, just log and keep listening
                    logger.warning(f"Redis socket timeout (no data): {e}, continuing to listen")
                    continue
                except redis.exceptions.ConnectionError as e:
                    logger.error(f"Connection error during message processing: {e}")
                    break  # go reconnectdwa
                except Exception as e:
                    logger.error(f"Unexpected error during message processing: {e}")
        
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        
        # We'll reach here if the inner loop breaks due to an error 3333dwdwaddddwwww
        retry_count += 1
        if retry_count < max_retries:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            # Exponential backoff for retry delayfe
            retry_delay = min(retry_delay * 2, 60)  # Max 60 secondsxxxx
            logger.info(f"Retry delay increased to {retry_delay} seconds")
        else:
            logger.error("Escaped from the retry loop")
            logger.error(f"Max retries ({max_retries}) reached. Giving up.")
            break # exit the loopswdw
    logger.info("Exiting log-message-processor")