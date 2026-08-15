import unittest

from transform_adf_template import transform


class TransformAdfTemplateTests(unittest.TestCase):
    def setUp(self):
        self.template = {
            "resources": [
                {
                    "name": "[concat(parameters('factoryName'), '/ir_dev')]",
                    "type": "Microsoft.DataFactory/factories/integrationRuntimes",
                    "properties": {"type": "Managed"},
                },
                {
                    "name": "[concat(parameters('factoryName'), '/ls_keyvault')]",
                    "type": "Microsoft.DataFactory/factories/linkedServices",
                    "dependsOn": [
                        "[concat(resourceId('Microsoft.DataFactory/factories/integrationRuntimes', parameters('factoryName'), 'ir_dev'))]"
                    ],
                    "properties": {
                        "typeProperties": {
                            "baseUrl": "https://sample-dev-kv.vault.azure.net/"
                        },
                        "connectVia": {
                            "referenceName": "ir_dev",
                            "type": "IntegrationRuntimeReference",
                        },
                    },
                },
                {
                    "name": "[concat(parameters('factoryName'), '/default/mpe_adls')]",
                    "type": "Microsoft.DataFactory/factories/managedVirtualNetworks/managedPrivateEndpoints",
                    "properties": {"privateLinkResourceId": "/subscriptions/dev/storage"},
                },
            ]
        }

    def test_stable_names_need_no_mapping(self):
        result = transform(self.template, {})
        self.assertEqual(len(result["resources"]), 1)
        self.assertEqual(result["resources"][0]["type"], "Microsoft.DataFactory/factories/linkedServices")

    def test_mapping_updates_resource_and_references(self):
        result = transform(
            self.template,
            {"artifactNameMappings": {"integrationRuntime": {"ir_dev": "ir_sit"}}},
        )
        self.assertEqual(
            result["resources"][0]["properties"]["connectVia"]["referenceName"],
            "ir_sit",
        )
        self.assertEqual(result["resources"][0]["dependsOn"], [])

    def test_property_override_targets_resource_by_type_and_name(self):
        result = transform(
            self.template,
            {
                "propertyOverrides": [
                    {
                        "resourceType": "Microsoft.DataFactory/factories/linkedServices",
                        "resourceName": "ls_keyvault",
                        "path": "/properties/typeProperties/baseUrl",
                        "value": "https://sample-sit-kv.vault.azure.net/",
                    }
                ]
            },
        )
        self.assertEqual(
            result["resources"][0]["properties"]["typeProperties"]["baseUrl"],
            "https://sample-sit-kv.vault.azure.net/",
        )

    def test_ir_and_private_endpoint_resources_are_excluded(self):
        result = transform(self.template, {})
        resource_types = {resource["type"] for resource in result["resources"]}
        self.assertNotIn("Microsoft.DataFactory/factories/integrationRuntimes", resource_types)
        self.assertNotIn(
            "Microsoft.DataFactory/factories/managedVirtualNetworks/managedPrivateEndpoints",
            resource_types,
        )

    def test_forbidden_value_fails_validation(self):
        with self.assertRaisesRegex(ValueError, "Forbidden source-environment"):
            transform(self.template, {"forbiddenValues": ["sample-dev-kv"]})


if __name__ == "__main__":
    unittest.main()