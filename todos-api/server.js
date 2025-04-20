'use strict';
const express = require('express')
const bodyParser = require("body-parser")
const jwt = require('express-jwt')

const ZIPKIN_URL = process.env.ZIPKIN_URL || 'http://127.0.0.1:9411/api/v2/spans';
const {Tracer, 
  BatchRecorder,
  jsonEncoder: {JSON_V2}} = require('zipkin');
  const CLSContext = require('zipkin-context-cls');  
const {HttpLogger} = require('zipkin-transport-http');
const zipkinMiddleware = require('zipkin-instrumentation-express').expressMiddleware;

const logChannel = process.env.REDIS_CHANNEL || 'log_channel';
const redisHost = process.env.REDIS_HOST || 'localhost';
const redisPort = process.env.REDIS_PORT || 6379;
const redisPassword = process.env.REDIS_PASSWORD ;
const redis = require('redis');
const redisOptions = {
  host: redisHost,
  port: redisPort,
  retry_strategy: function (options) {
     
       if (options.error && options.error.code === 'ECONNREFUSED') {
           return new Error('The server refused the connection');
       }
       
       if (options.error && options.error.code === 'NOAUTH') {
           console.error('Redis Authentication failed! Check REDIS_PASSWORD.');
           return new Error('Redis authentication failed'); // Stop retrying on auth failure
       }
       if (options.total_retry_time > 1000 * 60 * 5) { // 5 mins
           return new Error('Retry time exhausted');
       }
       if (options.attempt > 10) {
           console.log('Max Redis connection attempts reached.');
           return new Error('Max Redis connection attempts reached.');
       }
       console.log(`Redis retry attempt: ${options.attempt}, Error: ${options.error ? options.error.code : 'None'}`);
       return Math.min(options.attempt * 100, 3000);
  }
};

if (redisPassword) {
  redisOptions.password = redisPassword;
}

if (redisHost.endsWith('.redis.cache.windows.net')) {
  console.log("Configuring Redis client for TLS (v2.8 method)");
  redisOptions.tls = {
    
    servername: redisHost,
    
  };
} else {
    console.log("Not configuring Redis client for TLS (host does not match Azure pattern)");
}//you can remove this if you are not using Azure Redis Cachewdwd

console.log(`Redis options: ${JSON.stringify(redisOptions)}`);
console.log(`Attempting to connect to Redis (v2.8) at ${redisHost}:${redisPort}`);
const redisClient = redis.createClient(redisOptions); 

redisClient.on('error', (err) => {
  console.error('Redis Client Error:', err);
});

redisClient.on('ready', () => {
  console.log('Redis Client is ready.');
});

redisClient.on('reconnecting', (params) => {
    console.log('Redis Client is reconnecting:', params ? `Delay: ${params.delay}, Attempt: ${params.attempt}` : '');
});
const port = process.env.TODO_API_PORT || 8082
const jwtSecret = process.env.JWT_SECRET || "foo"

const app = express()

// tracing
const ctxImpl = new CLSContext('zipkin');
const recorder = new  BatchRecorder({
  logger: new HttpLogger({
    endpoint: ZIPKIN_URL,
    jsonEncoder: JSON_V2
  })
});
const localServiceName = 'todos-api';
const tracer = new Tracer({ctxImpl, recorder, localServiceName});


app.use(jwt({ secret: jwtSecret }))
app.use(zipkinMiddleware({tracer}));
app.use(function (err, req, res, next) {
  if (err.name === 'UnauthorizedError') {
    res.status(401).send({ message: 'invalid token' })
  }
})
app.use(bodyParser.urlencoded({ extended: false }))
app.use(bodyParser.json())

const routes = require('./routes')
routes(app, {tracer, redisClient, logChannel})

app.listen(port, function () {
  console.log('todo list RESTful API server started on: ' + port)
})
