#!/usr/bin/env python3
import os

import aws_cdk as cdk

from network_stack import NetworkStack
from server_stack import ServerStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

# Stack 1: VPC with a public and a private subnet in each of two Availability Zones
network = NetworkStack(app, "NetworkStack", env=env)

# Stack 2: web servers, MySQL RDS instance, security groups and load balancer
ServerStack(app, "ServerStack", vpc=network.vpc, env=env)

app.synth()
