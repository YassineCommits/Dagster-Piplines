job "dagster-user-code-git" {
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

    task "git-clone" {
      driver = "docker"
      
      config {
        image = "alpine:latest"
        command = "sh"
        args = [
          "-c",
          "apk add --no-cache git && cd /tmp && rm -rf pipelines && git clone https://github.com/YassineCommits/Dagster-Piplines.git temp_repo && cp -r temp_repo/pipelines pipelines && rm -rf temp_repo && echo 'Git clone completed successfully' && ls -la pipelines"
        ]
        volumes = [
          "/tmp:/tmp"
        ]
      }

      resources {
        cpu    = 50
        memory = 128
      }

      lifecycle {
        hook = "prestart"
        sidecar = false
      }
    }

    task "dagster-user-code" {
      driver = "docker"

      config {
        image      = "public.ecr.aws/r5v1v2m1/dagster-user-code:latest"
        force_pull = true
        ports      = ["grpc"]
        volumes = [
          "/tank/data:/tank/data",
          "/tmp/pipelines:/opt/dagster/app/pipelines"
        ]
        command = "bash"
        args = [
          "-c",
          "cd /opt/dagster/app && pip install -e pipelines && dagster code-server start -h 0.0.0.0 -p 3030 -m pipelines.definitions"
        ]
      }

      env {
        GUEPARD_POSTGRES_USER     = "guepard-admin"
        GUEPARD_POSTGRES_PASSWORD = "sGtCa0xj2sM6"
      }

      resources {
        cpu    = 500
        memory = 1024
      }
    }
  }
}
