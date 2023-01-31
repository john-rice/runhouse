from typing import Optional

from .folder import Folder


class GCSFolder(Folder):
    RESOURCE_TYPE = 'folder'
    DEFAULT_FS = 'gcp'

    def __init__(self, dryrun: bool, **kwargs):
        super().__init__(dryrun=dryrun, **kwargs)

    @staticmethod
    def from_config(config: dict, dryrun=True):
        """ Load config values into the object. """
        return GCSFolder(**config, dryrun=dryrun)

    def empty_folder(self):
        """ Remove gcs folder contents, but not the folder itself. """
        for p in self.fsspec_fs.ls(self.url):
            self.fsspec_fs.rm(p)

    def delete_in_fs(self, recurse=True, *kwargs):
        """ Delete the gcs folder itself along with its contents. """
        try:
            from sky.data.storage import GcsStore
            GcsStore(name=self.bucket_name_from_url(self.url), source=self._fsspec_fs).delete()
        except Exception as e:
            raise e

    def upload(self, src: str, region: Optional[str] = None):
        """ Upload a folder to an GCS bucket. """
        from sky.data.storage import GcsStore

        # NOTE: The sky GcsStore.upload() API does not let us specify the folder within the bucket to upload to.
        # This means we have to use the CLI command for performing the actual upload using sky's `run_upload_cli`

        # Initialize the GcsStore object which creates the bucket if it does not exist
        gcs_store = GcsStore(name=self.bucket_name_from_url(self.url), source=src, region=region)

        sync_dir_command = self.upload_command(src=src, dest=self.url)
        self.run_upload_cli_cmd(sync_dir_command, access_denied_message=gcs_store.ACCESS_DENIED_MESSAGE)

    def upload_command(self, src: str, dest: str):
        # https://github.com/skypilot-org/skypilot/blob/983f5fa3197fe7c4b5a28be240f7b027f7192b15/sky/data/storage.py#L1240
        dest = dest.lstrip("/")
        return f'gsutil -m rsync -r -x \'.git/*\' {src} gs://{dest}'

    @staticmethod
    def download(remote_dir, local_dir):
        """ Download a folder from a GCS bucket to local dir. """
        # NOTE: Sky doesn't support this API yet for each provider - for now we'll use sky's `_download_remote_dir`
        # https://github.com/skypilot-org/skypilot/blob/983f5fa3197fe7c4b5a28be240f7b027f7192b15/sky/data/storage.py#L231
        from sky.data.storage import StoreType
        return Folder.download_from_remote(remote_dir=remote_dir,
                                           local_dir=local_dir,
                                           bucket_type=StoreType.GCS)

    def download_command(self, src, dest):
        from sky.cloud_stores import GcsCloudStorage
        download_command = GcsCloudStorage().make_sync_dir_command(src, dest)
        return download_command

    def to_cluster(self, dest_cluster, url=None, mount=False, return_dest_folder=False):
        upload_command = self.upload_command(src=self.url, dest=url)
        dest_cluster.run([upload_command])
        if return_dest_folder:
            return GCSFolder(url=url, dryrun=True).from_cluster(dest_cluster)

    def to_local(self, dest_url: str, data_config: dict, return_dest_folder: Optional[bool] = False):
        """ Copy a folder from an GCS bucket to local dir. """
        self.download(remote_dir=self.url, local_dir=dest_url)
        if return_dest_folder:
            return self.destination_folder(dest_url=dest_url, dest_fs='file', data_config=data_config)

    def to_data_store(self,
                      fs: str,
                      data_store_url: Optional[str] = None,
                      data_config: Optional[dict] = None,
                      return_dest_folder: Optional[bool] = True):
        """ Copy folder from GCS to another remote data store (ex: GCS, S3, Azure) """
        if fs == 'gcs':
            # Transfer between GCS folders
            from sky.data.storage import GcsStore
            sync_dir_command = self.upload_command(src=self.url, dest=data_store_url)
            self.run_upload_cli_cmd(sync_dir_command, access_denied_message=GcsStore.ACCESS_DENIED_MESSAGE)
        elif fs == 's3':
            from sky.data import data_transfer
            # Note: The sky data transfer API only allows for transfers between buckets, not specific directories.
            data_transfer.gcs_to_s3(gs_bucket_name=self.bucket_name_from_url(self.url),
                                    s3_bucket_name=self.bucket_name_from_url(data_store_url))
        elif fs == 'azure':
            raise NotImplementedError('Azure not yet supported')
        else:
            raise ValueError(f'Invalid fs: {fs}')

        if return_dest_folder:
            return self.destination_folder(dest_url=data_store_url, dest_fs=fs, data_config=data_config)