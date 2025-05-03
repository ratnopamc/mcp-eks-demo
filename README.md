# mcp-eks-demo

## 🗂️ Project Structure

```
├── infra/                # Terraform code for EKS, VPC, ALB, etc.
│   ├── main.tf
│   ├── variables.tf
│   └── terraform.tfvars
├── mcp/                  # MCP server code (Python)
│   ├── server.py
|   |-- client.py
│   ├── tools/
│   │   └── weather.py
│   └── requirements.txt
├── deploy/               # Dockerfile, Kubernetes YAMLs
│   ├── Dockerfile
│   ├── mcp.yaml
└── README.md
```
