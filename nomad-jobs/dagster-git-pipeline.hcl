job "dagster-git-pipeline" {
  datacenters = ["us-west-aws"]
  type        = "service"
  node_pool   = "us-west-aws"

  group "dagster-git-group" {
    count = 1

    constraint {
      attribute = "${meta.compute}"
      value     = "true"
    }

    network {
      port "http" {
        static = 3000
      }
      port "grpc" {
        static = 3030
      }
    }

    task "git-clone" {
      driver = "raw_exec"
      
      config {
        command = "/bin/bash"
        args = [
          "-c",
          "cd /tank/pipelines && rm -rf hello_world_pipeline && git clone https://github.com/YassineCommits/Dagster-Piplines.git temp_repo && cp -r temp_repo/pipelines/hello_world_pipeline . && rm -rf temp_repo && echo 'Git clone completed successfully'"
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
        image      = "python:3.10-slim"
        force_pull = true
        ports      = ["grpc"]
        volumes = [
          "/tank/data:/tank/data",
          "/tank/pipelines:/opt/dagster/app/pipelines"
        ]
        command = "bash"
        args = [
          "-c",
          "cd /opt/dagster/app && pip install dagster==1.7.3 dagster-postgres==0.23.3 duckdb pandas numpy pyarrow && cd pipelines && pip install -e . && dagster code-server start -h 0.0.0.0 -p 3030 -m hello_world_pipeline.definitions"
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

      depends_on {
        task = "git-clone"
      }
    }

    task "dagster-daemon" {
      driver = "docker"

      config {
        image      = "public.ecr.aws/r5v1v2m1/dagster-system:latest"
        force_pull = true
        command    = "dagster-daemon"
        args       = ["run"]
        volumes = [
          "/var/run/docker.sock:/var/run/docker.sock"
        ]
      }

      env {
        GUEPARD_POSTGRES_USER     = "guepard-admin"
        GUEPARD_POSTGRES_PASSWORD = "sGtCa0xj2sM6"
      }

      resources {
        cpu    = 100
        memory = 256
      }
    }

    task "dagster-webserver" {
      driver = "docker"

      config {
        image      = "public.ecr.aws/r5v1v2m1/dagster-system:latest"
        force_pull = true
        command    = "dagster-webserver"
        args = [
          "-h",
          "0.0.0.0",
          "-p",
          "3000",
          "-w",
          "workspace.yaml"
        ]
        ports = ["http"]
      }

      env {
        GUEPARD_POSTGRES_USER     = "guepard-admin"
        GUEPARD_POSTGRES_PASSWORD = "sGtCa0xj2sM6"
      }

      service {
        name     = "guepard-dagster-git"
        port     = "http"
        provider = "nomad"
        tags = [
          "traefik.enable=true",
          "traefik.http.routers.dagster-git.rule=Host(`dagster-git.dev.guepard.run`)",
          "traefik.http.routers.dagster-git.entrypoints=websecure",
          "traefik.http.routers.dagster-git.tls.certresolver=letsencrypt"
        ]
      }

      resources {
        cpu    = 300
        memory = 512
      }
    }
  }
}
