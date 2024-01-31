import argparse
from google.cloud import datacatalog
from google.cloud.datacatalog_v1beta1.types import Taxonomy
from google.cloud import bigquery_datapolicies_v1
import os
import uuid
from helper_functions.create_policy_tag_taxonomy import create_taxonomy, create_policy_tags


class PolicyTagManager:
    def __init__(self, sa, project_id: str, region: str):
        # Create a client
        self.data_policy_client = bigquery_datapolicies_v1.DataPolicyServiceClient()
        self.policy_tag_client = datacatalog.PolicyTagManagerClient()
        self.project_id = project_id
        self.region = region
        self.location = f"projects/{project_id}/locations/{region}"

    def get_taxonomy(self, taxonomy_id: str):
        """ Get a policy tag taxonomy details
        @param taxonomy_id: LIKE 5522375742982095037
        @return: struct with detaiils
        """
        taxonomy_name = os.path.join(self.location, "taxonomies", taxonomy_id)
        request = datacatalog.GetTaxonomyRequest(
            name=taxonomy_name,
        )
        response = self.policy_tag_client.get_taxonomy(request=request)
        return response

    def list_taxonomies(self):
        """ Get all setted policy tag taxonomies
        @return: list of taxonomies
        """
        request = datacatalog.ListTaxonomiesRequest(
            parent=self.location,
        )
        page_result = self.policy_tag_client.list_taxonomies(request=request)
        # Handle the response
        taxos = list()
        for response in page_result:
            taxos.append(response)
        return taxos

    def create_taxonomy(self, taxonomy_name):
        """ Create a policy tag taxonomy
        @param taxonomy_name:
        @return:
        """
        return create_taxonomy(self.project_id, self.region, taxonomy_name)

    def delete_taxonomy(self):
        pass

    def get_policy_tag(self, policy_tag_name):
        # Create a client
        # Initialize request argument(s)
        request = datacatalog.GetPolicyTagRequest(
            name=policy_tag_name,
        )
        response = self.policy_tag_client.get_policy_tag(request=request)
        return response

    def list_policy_tags(self):
        # Initialize request argument(s)
        request = datacatalog.ListPolicyTagsRequest(
            parent=self.location,
        )
        # Make the request
        page_result = self.policy_tag_client.list_policy_tags(request=request)
        # Handle the response
        ptags = list()
        for response in page_result:
            ptags.append(response)
        return ptags

    def create_policy_tags(self, taxonomy_name, policy_tag_labels):
        return create_policy_tags(taxonomy_name, policy_tag_labels)

    def create_data_policy(self, taxonomy_id, policy_tag_id, predefined_expression):
        """ Create a data policy with DATA_MASKING_POLICY
        @param taxonomy_id:
        @param policy_tag_id:
        @param predefined_expression: str, values: Values:
            SHA256
            ALWAYS_NULL
            DEFAULT_MASKING_VALUE
            LAST_FOUR_CHARACTERS
            FIRST_FOUR_CHARACTERS
            EMAIL_MASK
            DATE_YEAR_MASK
        @return: True
        """
        # Initialize request argument(s)
        data_policy = bigquery_datapolicies_v1.DataPolicy()

        # Create a Data Policy
        data_policy.data_policy_type = "DATA_MASKING_POLICY"
        data_policy.data_policy_id = str(uuid.uuid1().hex)
        data_policy.data_masking_policy.predefined_expression = predefined_expression
        data_policy.policy_tag = f"projects/{self.project_id}/locations/{self.region}/taxonomies/{taxonomy_id}/policyTags/{policy_tag_id}"
        parent = f'projects/{self.project_id}/locations/{self.region}'

        # Create a Sync request
        request = bigquery_datapolicies_v1.CreateDataPolicyRequest(
            parent=parent,
            data_policy=data_policy,
        )
        # Make the request
        response = self.data_policy_client.create_data_policy(request=request)

        # Handle the response
        print(response)
