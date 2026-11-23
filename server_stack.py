from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_elasticloadbalancingv2_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_rds as rds
from constructs import Construct


class ServerStack(Stack):
    """Two web servers (one per public subnet), a MySQL RDS instance and an ALB."""

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ---------- Security groups ----------
        web_sg = ec2.SecurityGroup(
            self,
            "WebServerSG",
            vpc=vpc,
            description="Web servers: HTTP from anywhere",
            allow_all_outbound=True,
        )
        web_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP from anywhere")

        db_sg = ec2.SecurityGroup(
            self,
            "DatabaseSG",
            vpc=vpc,
            description="RDS MySQL: port 3306 only from the web servers security group",
            allow_all_outbound=False,
        )
        db_sg.add_ingress_rule(web_sg, ec2.Port.tcp(3306), "MySQL from web servers only")

        # ---------- Web servers ----------
        role = iam.Role(
            self,
            "WebServerRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
            ],
        )

        # User data from the CloudFormation assignment
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "dnf update -y",
            "dnf install -y git httpd php",
            "service httpd start",
            "chkconfig httpd on",
            "aws s3 cp s3://seis665-public/index.php /var/www/html/",
        )

        public_subnets = vpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC).subnets

        web_servers = []
        for i, subnet in enumerate(public_subnets, start=1):
            instance = ec2.Instance(
                self,
                f"WebServer{i}",
                instance_name=f"web{i}",
                instance_type=ec2.InstanceType("t3.micro"),
                machine_image=ec2.MachineImage.latest_amazon_linux2023(),
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(subnets=[subnet]),
                security_group=web_sg,
                role=role,
                user_data=user_data,
            )
            web_servers.append(instance)

        # ---------- RDS MySQL in the private subnets ----------
        subnet_group = rds.SubnetGroup(
            self,
            "DbSubnetGroup",
            description="All private subnets",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            removal_policy=RemovalPolicy.DESTROY,
        )

        database = rds.DatabaseInstance(
            self,
            "Database",
            engine=rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_0),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            vpc=vpc,
            subnet_group=subnet_group,
            security_groups=[db_sg],
            allocated_storage=20,
            multi_az=False,
            publicly_accessible=False,
            database_name="webappdb",
            credentials=rds.Credentials.from_generated_secret("admin"),
            backup_retention=Duration.days(0),
            deletion_protection=False,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ---------- Application Load Balancer ----------
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "WebLoadBalancer",
            vpc=vpc,
            internet_facing=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=web_sg,
        )
        listener = alb.add_listener("HttpListener", port=80, open=True)
        listener.add_targets(
            "WebServers",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[targets.InstanceTarget(server, 80) for server in web_servers],
            health_check=elbv2.HealthCheck(path="/", interval=Duration.seconds(30)),
        )

        # ---------- Outputs ----------
        CfnOutput(self, "LoadBalancerDNS", value=alb.load_balancer_dns_name)
        CfnOutput(self, "DatabaseEndpoint", value=database.db_instance_endpoint_address)
        CfnOutput(self, "DatabaseSecretArn", value=database.secret.secret_arn)
