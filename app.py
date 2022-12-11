#!/usr/bin/env python3

import aws_cdk as core

from cdk_lib.ECSStack import ECSStack
from cdk_lib.DynamoDBStack import DynamoDBStack

props = {
            'namespace':'OnBoard',
            'vpc_name':'vpc-onboard',
            'image_id':'111111111.dkr.ecr.us-east-1.amazonaws.com/test-ecs-cdk-app:latest',
            'cidr':'10.0.0.0/16',
            'web_port': 8080,
            'app_name':'myEbApp'
        }


app = core.App()
preferred_region = app.node.try_get_context("preferred_region")
account_id = app.node.try_get_context("account_id")

env = core.Environment(region=preferred_region, account=account_id)

db_stack = DynamoDBStack(app, f"{props['namespace']}-Dynamo",props,env=env)

ecs_stack = ECSStack(app, f"{props['namespace']}-ECS",db_stack.output_props, db_stack=db_stack, env=env)
ecs_stack.add_dependency(db_stack)

app.synth()
