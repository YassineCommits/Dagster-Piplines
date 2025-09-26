job "dagster-user-code-git-simple" {
  datacenters = ["us-west-aws"]
  type        = "service"
  node_pool   = "us-west-aws"

  group "dagster-user-code-group" {
    count = 1

    constraint {
      attribute = "${meta.compute}"
      value     = "true"
    }

    network {
      port "grpc" {
        static = 3030
      }
    }

    task "dagster-user-code" {
      driver = "docker"

      config {
        image      = "public.ecr.aws/r5v1v2m1/dagster-user-code:latest"
        force_pull = true
        ports      = ["grpc"]
        volumes = [
          "/tank/data:/tank/data"
        ]
        command = "bash"
        args = [
          "-c",
          "cd /opt/dagster/app && git clone https://github.com/YassineCommits/Dagster-Piplines.git temp_repo && cp -r temp_repo/pipelines/* pipelines/ && rm -rf temp_repo && pip install -e pipelines && dagster code-server start -h 0.0.0.0 -p 3030 -m pipelines.hello_world_pipeline.definitions"
        ]
      }

      env {
        GUEPARD_POSTGRES_USER     = "guepard-admin"
        GUEPARD_POSTGRES_PASSWORD = "sGtCa0xj2sM6"
      }

      service {
        name     = "guepard-dagster-user-code"
        port     = "grpc"
        provider = "nomad"
      }

      resources {
        cpu    = 500
        memory = 1024
      }
    }
  }
}
