from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class NetworkStack(Stack):
    """One public and one private subnet in each of two Availability Zones."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "WebVpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            nat_gateways=0,  # nothing in the private subnets needs Internet access
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        CfnOutput(self, "VpcId", value=self.vpc.vpc_id)
