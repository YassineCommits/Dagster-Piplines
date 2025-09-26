job "dagster-production-system" {
  datacenters = ["us-west-aws"]
  type        = "service"
  node_pool   = "us-west-aws"

  group "dagster-system-group" {
    count = 1

    constraint {
      attribute = "${meta.compute}"
      value     = "true"
    }

    network {
      port "http" {
        static = 3000
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
          "/opt/dagster/workspace.yaml"
        ]
        ports = ["http"]
        volumes = [
          "/opt/dagster/workspace.yaml:/opt/dagster/workspace.yaml"
        ]
      }

      env {
        GUEPARD_POSTGRES_USER     = "guepard-admin"
        GUEPARD_POSTGRES_PASSWORD = "sGtCa0xj2sM6"
      }

      service {
        name     = "guepard-dagster-system"
        port     = "http"
        provider = "nomad"
        tags = [
          "traefik.enable=true",
          "traefik.http.routers.dagster-system.rule=Host(`dagster-system.dev.guepard.run`)",
          "traefik.http.routers.dagster-system.entrypoints=websecure",
          "traefik.http.routers.dagster-system.tls.certresolver=letsencrypt"
        ]
      }

      resources {
        cpu    = 300
        memory = 512
      }
    }
  }
}
