from django.db import models
from uuid import uuid4


class Comment(models.Model):
    """Comment attached to some object (target) identified by its uuid.
    """

    comment_uuid = models.UUIDField(primary_key=True, default=uuid4)
    target_uuid = models.UUIDField()
    author_uuid = models.UUIDField()
    text = models.TextField()
    created_ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = "created_ts"


class CommentView(models.Model):
    """A record of someone viewing a single comment.
    """

    view_uuid = models.UUIDField(primary_key=True, default=uuid4)
    comment_uuid = models.UUIDField()
    viewer_uuid = models.UUIDField()
    created_ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = "created_ts"


class DataLog(models.Model):
    """A record of an operation on some data.  
    Stores the inputs and basic metadata for the operation.
    """

    operation_uuid = models.UUIDField(primary_key=True, default=uuid4)
    operation_name = models.TextField()
    source = models.TextField()
    source_version = models.TextField()
    created_ts = models.DateTimeField(auto_now_add=True)
    data = models.TextField()

    class Meta:
        get_latest_by = "created_ts"
