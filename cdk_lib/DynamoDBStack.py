from aws_cdk import (
    aws_dynamodb,
    custom_resources as cr,
    Duration, Stack, RemovalPolicy
)

import pandas as pd
import uuid

from constructs import Construct

class DynamoDBStack(Stack):

    # This function parses a CSV file for importing into DynamDB
    # This API call has a limit, so the data needs to be split into several calls.
    # In future, probably want to use Lambda directly.
    def prepare_import_data(self, data):
        csv_file_path = f"data/{data}.csv"
        df = pd.read_csv(csv_file_path)
        the_list=[]

        # https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_PutRequest.html
        for index, row in df.iterrows():
            the_list.append(
                {
                "PutRequest": {
                    "Item": {
                        'category': {'S': row[3]},
                        'title': {'S': row[0]},
                        'id':{'S': str(uuid.uuid4())},
                        'content': {
                            'M': {
                                'link': {'S': row[1]},
                                'description':{'S': row[2]}
                            }
                        }
                    }
                }
                }
            )
        return the_list

    def __init__(self, scope: Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

     # create DynamoDB Table for Resources
        resource_table = aws_dynamodb.Table(
            self, "resources",
            table_name="resources",
            partition_key=aws_dynamodb.Attribute(
                name="id",
                type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="category",
                type=aws_dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY
        )
        # Create GSI
        # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html
        resource_table.add_global_secondary_index(index_name="gsiIndex",
            partition_key=aws_dynamodb.Attribute(
                name="category",
                type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="id",
                type=aws_dynamodb.AttributeType.STRING
            )
        )

        # create DynamoDB Table for Bookmarks
        bookmark_table = aws_dynamodb.Table(
            self, "bookmarks",
            table_name="bookmarks",
            partition_key=aws_dynamodb.Attribute(
                name="id",
                type=aws_dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        # create DynamoDB Table for Category
        category_table = aws_dynamodb.Table(
            self, "categories",
            table_name="categories",
            partition_key=aws_dynamodb.Attribute(
                name="category",
                type=aws_dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        resource_1_custom = cr.AwsCustomResource(self, "resource_1_custom",
        on_create=cr.AwsSdkCall(
            service="DynamoDB",
            action="batchWriteItem",
            parameters={
                "RequestItems": {
                    "resources": self.prepare_import_data("resource1")
                    }
            },
            physical_resource_id=cr.PhysicalResourceId.of("resource_1_custom")
        ),
        policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
            resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            )
        )

        resource_2_custom = cr.AwsCustomResource(self, "resource_2_custom",
            on_create=cr.AwsSdkCall(
                service="DynamoDB",
                action="batchWriteItem",
                parameters={
                   "RequestItems": {
                       "resources": self.prepare_import_data("resource2")
                       }
                },
                physical_resource_id=cr.PhysicalResourceId.of("resource_2_custom")
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            )
        )

        self.output_props = props.copy()

        self.myResourceTable = resource_table
        self.myCatTable = category_table
        self.myBookTable = bookmark_table
