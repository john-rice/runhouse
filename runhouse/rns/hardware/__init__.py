from .cluster import cluster, Cluster
from .on_demand_cluster import autocluster, OnDemandCluster

# TODO KubeRayCluster, AnyscaleRayCluster etc.
#  Other cluster types: Spark? Bare Kubernetes (e.g. EKS, GKS)?
# DaskCluster - should be easy to do with SkyPilot: https://docs.dask.org/en/stable/deploying-ssh.html
