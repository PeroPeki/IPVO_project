# Project within college course: Big Data Infrastructure (IPVO)

### 1st PHASE: 
Users can browse the list of events, book a ticket for the selected event, and reserve a table in the nightclub. The system consists of multiple instances of web servers in Docker containers behind a Traefik load balancer that distributes requests for scalability and resilience. User data, events, tables, and reservations are stored in a NoSQL MongoDB database.


### 2nd PHASE: 
Real-time display of table status and availability, so every change is immediately visible to all users. For each new reservation or cancellation, the backend sends an event through the RabbitMQ streaming service, allowing client applications to automatically refresh the display without reloading the page. The phase focus is on real-time updates and reliable event transmission within the system. It also introduces functionality for periodic analysis of event and club attendance data, along with generating daily and monthly reports.

### 3rd PHASE: 
To speed up read operations, a caching system (Redis) is introduced for frequently requested data, which refreshes with every new or canceled reservation, such as lists of upcoming events and current table availability. For better system performance oversight, basic monitoring and centralized metrics collection are implemented. Key application metrics will be collected by Prometheus (request count, response time, error rate), with visualization through dashboards for real-time performance and load tracking performed using Grafana. 
