module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "~> 19.15"
  cluster_name    = "mcp-on-eks"
  cluster_version = "1.31"

  cluster_addons = {
    coredns                = {}
    eks-pod-identity-agent = {}
    kube-proxy             = {}
    vpc-cni                = {}
  }

  manage_aws_auth_configmap = true

  # Enable public access to the Kubernetes API server
  cluster_endpoint_public_access = true
  
  # Configure cluster access for kubectl
  cluster_endpoint_private_access = true
  
  # Ensure the security group allows access to the Kubernetes API
  create_cluster_security_group = true
  create_node_security_group = true

  subnet_ids         = module.vpc.private_subnets
  vpc_id             = module.vpc.vpc_id
  enable_irsa        = true
  

  eks_managed_node_groups = {
    mcp_nodes = {
      instance_types = ["m5.xlarge"]
      desired_size   = 2
      min_size       = 1
      max_size       = 3
      ami_type       = "BOTTLEROCKET_x86_64"
    }
  }

  tags = {
    Environment = "dev"
    Terraform   = "true"
  }
}

resource "aws_iam_policy" "alb_controller_policy" {
  name   = "AWSLoadBalancerControllerIAMPolicy"
  policy = file("${path.module}/iam_policy_alb_controller.json")
}

resource "aws_iam_role" "alb_controller_role" {
  name               = "alb-controller-sa-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Federated = module.eks.oidc_provider_arn
      },
      Action = "sts:AssumeRoleWithWebIdentity",
      Condition = {
        StringEquals = {
          "${module.eks.oidc_provider}:sub" = "system:serviceaccount:kube-system:aws-load-balancer-controller"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "alb_controller_attachment" {
  policy_arn = aws_iam_policy.alb_controller_policy.arn
  role       = aws_iam_role.alb_controller_role.name
}

resource "kubernetes_service_account" "alb_controller_sa" {
  metadata {
    name      = "aws-load-balancer-controller"
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.alb_controller_role.arn
    }
  }
  depends_on = [module.eks]
}

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"
  version    = "1.7.1"

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "serviceAccount.create"
    value = "false"
  }

  set {
    name  = "serviceAccount.name"
    value = kubernetes_service_account.alb_controller_sa.metadata[0].name
  }

  set {
    name  = "region"
    value = var.region
  }

  set {
    name  = "vpcId"
    value = module.vpc.vpc_id
  }

  depends_on = [kubernetes_service_account.alb_controller_sa]
}

resource "kubernetes_secret" "openweather" {
  metadata {
    name      = "openweather-api"
    namespace = "default"
  }

  data = {
    API_KEY = var.openweather_api_key
  }

  type = "Opaque"
  depends_on = [module.eks]
}