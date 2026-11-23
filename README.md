# CDK homework: website on EC2 instances with RDS

Two CDK (Python) stacks:

- `NetworkStack` (`network_stack.py`): VPC with one public and one private subnet in each of two Availability Zones.
- `ServerStack` (`server_stack.py`): two web servers (one per public subnet), an RDS MySQL instance using the private subnets as its subnet group, security groups (web: port 80 from anywhere; database: port 3306 only from the web servers' security group), and an Application Load Balancer in front of the web servers.

Commands:

    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cdk bootstrap
    cdk deploy --all
    cdk destroy --all
