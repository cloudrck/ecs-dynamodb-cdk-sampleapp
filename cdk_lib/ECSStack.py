from aws_cdk import (
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
    Stack, CfnOutput
)

import json, os
from constructs import Construct

class ECSStack(Stack):

    def __init__(self, scope: Construct, id: str, props, db_stack, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create VPC, Fargate will create everything else in the VPC
        vpc = ec2.Vpc(
                    self, props['vpc_name'],
                    enable_dns_hostnames=True,
                    enable_dns_support=True,
                    cidr= props['cidr'],
                    max_azs=2
                )
        # Hold cluster object for creation.
        cluster = ecs.Cluster(
            self, 'ECSCluster',
            vpc=vpc
        )
        appName = props['app_name']

        # Add IAM Policy to Fargate Execution Role to read from ECR our repo.
        myRole = iam.Role(self, f"{appName}-aws-taskexecute-ecs-role",
            assumed_by= iam.ServicePrincipal('ecs-tasks.amazonaws.com')
            )

        # Pull AWS managed policy for use.
        managedPolicy = iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ContainerRegistryReadOnly')

        # Add the above managed policy to our Fargate Execution Role
        myRole.add_managed_policy(managedPolicy)

        # Launch ECS and ELB via Fargate. Pull from a repo
        # Threw in environment vars and docker labels for show.
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(self, "Service",
            cluster=cluster,
            desired_count=1,
            assign_public_ip=True,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry(props['image_id']),
                execution_role=myRole,
                container_port=props['web_port'],
                environment={
                    'DYNAMO_HOST': "NOT USED",
                    'DYNAMO_PORT': 'NOT USED'
                },
                docker_labels={
                    "application.label.one": "first_label",
                    "application.label.two": "second_label"
                }
            )
        )

        # Add ingress rule to the Security Group Fargate manages
        fargate_service.service.connections.security_groups[0].add_ingress_rule(
            peer = ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection = ec2.Port.tcp(props['web_port']),
            description="Allow http inbound from VPC"
        )

        # Grant Fargate Task Role ability to read/write to DynamDB Tables. Could probably restrict access further.
        db_stack.myResourceTable.grant_full_access(fargate_service.task_definition.task_role)
        db_stack.myCatTable.grant_full_access(fargate_service.task_definition.task_role)
        db_stack.myBookTable.grant_full_access(fargate_service.task_definition.task_role)

        # Print the Load Balancer URL
        CfnOutput(
            self, "LoadBalancerDNS",
            value=fargate_service.load_balancer.load_balancer_dns_name
        )
