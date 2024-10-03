# Pad-Lab-1
# 1) Application Suitability
## Why this idea is relevant
1. **Monetization of Content**: Subscription models allow creators to earn a stable income by offering exclusive content, and users get high-quality, ad-free experiences.
2. **Rise of Paid Subscriptions**: Growing consumer acceptance of paying for premium content supports the viability of subscription-based platforms.
3. **Niche Communities**: Subscription models help create focused communities around specific interests, driving higher engagement.
4. **Security and Content Ownership**: Creators maintain better control over their content and intellectual property in a subscription model, enhancing protection against unauthorized use.

## Why its implementation through distributed systems is necessary

1. **Scalability**: Distributed systems allow the platform to efficiently handle increasing amounts of data and users by scaling resources (*microservices*).
2. **High Availability and Reliability**: Redundancy in distributed systems ensures the platform remains accessible even during server failures.
3. **Data Consistency and Load Balancing**: Distributed systems manage data and requests efficiently, ensuring smooth performance and transaction handling.
4. **Efficient Resource Usage**: Distributed systems optimize resource allocation based on demand, preventing performance bottlenecks.
5. **Microservices Architecture**: Decoupling services in a distributed system improves scalability, fault tolerance, and platform flexibility.

# 2) Service Boundaries

![Diagram](/Checkpoint-1-Diagram.png "UML Diagram")

**Remarks:**
1. Web Socket connection is made from the client directly to the image sharing service for the link to be distributed to the clients at the exact time of it being published.
2. Image sharing service will save most used links in the Redis as a cache for a certain period of time so that it doesn't have to request to the database each time, (implement smth like if a link gets accessed 5 times in a window of 10 minutes save it to the cache for faster access)
3. Image sharing service makes a request to the authentification service to get the information if the user has rights of recieving the links and till when.

# 3) Technology Stack and Communication Patterns

1. Authentification + Billing Service
    + Python Flask
    + MySQL
2. Image Sharing Service
    + Python Flask
    + MySQL
    + Redis (caching)
    + WebSocket
3. API Gateway
    + GOLang
4. Service Discovery
    + GOLang

# 4) Data Management

**Autentification + Billing Service**
```
/register - Enter a new user in the database
/login - Enter the user into his account
/subscribe/{owner_name} - Pay subscription fee to the owner
/cancel-subscription - cancels autorenewable monthly subscription
/validate-user/{token} - used to validate user in case when he connects via web socket
```

**/register**
```
Method: Post
```
```
Sent data: 
{
    username:{username},
    password:{password}
}
```
```
Recieved data:
Status code 200:
{
    Response:"Account created"
}

Status code 401:
{
    Response:"username already exists"
}

Status code 401:
{
    Response:"Invalid character-use ".\|/ please use only alphanumerical values"
}
```

**/login**
```
Method: Post
```
```
Sent data:
{
    username:{username},
    password:{password}
}
```
```
Recieved data:
Status code 200:
{
    Response:"Loged in succesful",
    token:{token}
}
Status code 401:
{
    Response:"Invalid username/password please try again"
}
Status code 401:
{
    Response:"Invalid character-use ".\|/ please use only alphanumerical values"
}
```

**/subscribe/{owner_name}**
```
Method: Post
```
```
Sent data:
{
    user:{token},
    owner:{owner},
    card-info:{card-info},
    cvv:{cvv}
}
```
```
Recieved data:
Status code 200:
{
    Response:"Succesful payment done"
}
Status code 400:
{
    Response:"Invalid card information"
}
Status code 400:
{
    Response:"Insuficient funds"
}
```

**/cancel-subscription**
```
Method: Post
```
```
Sent data:
{
    user:{token},
    owner:{owner}
}
```
```
Status code 200:
{
    Response:"Succesful subscription canceled"
}
Status code 400:
{
    Response:"Invalid user information"
}
Status code 400:
{
    Response:"Invalid owner information"
}
```

**/validate-user/{token}**
```
Method: GET
```
```
Sent data: no sent data
```
```
Status code 200:
{
    Response:"User succesfuly validated",
    till-time:"11:09:2025"
}
Status code 400:
{
    Response:"User validation rejected"
}
```

**Image Sharing**

```
/upload - upload a picture to the server
/{owner} - get all picture links if you payed subscription
/{owner}/{image-id} - get a single picture if you payed subscription
/delete/{image-id} - delets a image if you are the owner of said image
localhost:9999 - websocket connection for instant image recieval
```

**/upload**
```
Method: Post
```
```
Sent data:
{
    user:{token},
    image:{image-binary} (!not sure as of yet)
}
```
```
Status code 200:
{
    Response:"Image succesfuly published"
}
Status code 400:
{
    Response:"user not found"
}
Status code 400:
{
    Response:"image not valid"
}
```

**/{owner}**
```
Method: Post
```
```
Sent data:
{
    user:{token}
}
```
```
Status code 200:
{
    Response:"Images succesfuly sent"
}
Status code 400:
{
    Response:"user not found"
}
Status code 400:
{
    Response:"owner not found"
}
```

**/{owner}/{image-id}**
```
Method: Post
```
```
Sent data:
{
    user:{token}
}
```
```
Status code 200:
{
    Response:"Image succesfuly sent"
}
Status code 400:
{
    Response:"user not found"
}
Status code 400:
{
    Response:"owner not found"
}
Status code 400:
{
    Response:"image not found"
}
```

**/delete/{image-id} - delets a image if you are the owner of said image**
```
Method: Post
```
```
Sent data:
{
    user:{token}
}
```
```
Status code 200:
{
    Response:"Image succesfuly deleted"
}
Status code 400:
{
    Response:"user not the owner of the image"
}
Status code 400:
{
    Response:"user not found"
}
Status code 400:
{
    Response:"image not found"
}
```

**/Notification**
```
Method: Websocket
```
```
Sent data:
{username} {password} {token}
```
```
Success: "Set up for instant recieval till {date}"
Error: "invalid username/password"
Error: "invalid token"
Error: "connection closed till date was reached"
```

# 5) Deployment and Scaling

Docker container will be used to separate services and other important structures, also docker compose will be used to scale horizontaly to the needs of the administrator or the system.