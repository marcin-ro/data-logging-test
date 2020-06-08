import functools
import json
import pytest
import uuid

from django.core.serializers.json import DjangoJSONEncoder
from django.db.transaction import atomic
from .models import Comment, CommentView, DataLog


def data_writer(writer_func):
    """A decorator that plugs writer_func into the logging machinery.

    It's dead simple now.  It limits writer_func to only accept kwargs to make
    all stored log entries consistent and annotated.

    Ideally it would detect nested calls, so that e.g. create_comment below
    would call store_comment_view and have those data_writers add two separate
    entries, but connected into a higher-level changeset.

    This is likely to run in an external transaction, but the decorator also
    opens a new transaction to be safe.

    All the example operations below follow the convention that models are
    read-only.  With some model tweaks we can probably effectively enforce
    that: only use models to read the data, use all the filtering niceties, but
    never use them directly to write to it, and strongly nudge developers in
    the direction of using data_writers.
    """

    @functools.wraps(writer_func)
    def wrapper(**kwargs):
        with atomic():
            # We can get a hold of the log entry here and provide it to all
            # operations, return it, connect it to higher-level operations (we can
            # detect that this is a nested data_writer).
            log = DataLog.objects.create(
                # We could also include the idea of adding an object's hash and
                # use it to prevent parallel operations on the same object, but
                # the calling code would be responsible of passing it here.
                operation_name=writer_func.__name__,
                data=DjangoJSONEncoder().encode(kwargs),
            )
            return writer_func(**kwargs)

    return wrapper


@data_writer
def create_comment(
    target_uuid: uuid.UUID, author_uuid: uuid.UUID, text: str
) -> Comment:
    """Create a comment.  Assume that authors see their own comments immediately.

    (just to demonstrate an operation on multiple tables)
    """
    comment = Comment.objects.create(
        target_uuid=target_uuid, author_uuid=author_uuid, text=text
    )
    comment_view = CommentView.objects.create(
        comment_uuid=comment.comment_uuid, viewer_uuid=comment.author_uuid
    )
    return comment


@data_writer
def edit_comment(comment_uuid: uuid.UUID, text: str):
    """Edit an existing comment.
    """
    rows_matched = Comment.objects.filter(uuid=comment_uuid).update(text=text)
    if rows_matched != 1:
        raise Exception("oh no")


@data_writer
def delete_comment(comment_uuid: uuid.UUID):
    """Delete a comment.
    """
    rows_deleted = Comment.objects.filter(uuid=comment_uuid).delete()
    if rows_deleted != 1:
        raise Exception("oh no")


@data_writer
def store_comment_view(comment_uuid: uuid.UUID, viewer_uuid: uuid.UUID) -> CommentView:
    """Store the information that someone viewed a comment.

    (very ineffective, but this is for demonstration only)
    """
    return CommentView.objects.create(
        comment_uuid=comment_uuid, viewer_uuid=viewer_uuid
    )


def test_operations(db):
    # create a comment
    create_comment(
        target_uuid="00000000-1234-5678-1234-567812345678",
        author_uuid="10000000-1234-5678-1234-567812345678",
        text="comment 1",
    )
    assert Comment.objects.count() == 1
    comment = Comment.objects.latest()
    assert str(comment.target_uuid) == "00000000-1234-5678-1234-567812345678"
    assert comment.text == "comment 1"

    # view it
    store_comment_view(
        comment_uuid="00000000-1234-5678-1234-567812345678",
        viewer_uuid="20000000-1234-5678-1234-567812345678",
    )
    comment_view = CommentView.objects.latest()
    assert str(comment_view.viewer_uuid) == "20000000-1234-5678-1234-567812345678"

    # check the logs
    logs = DataLog.objects.order_by("created_ts")
    assert len(logs) == 2
    first, second = logs
    assert first.operation_name == "create_comment"
    assert json.loads(first.data) == {
        "target_uuid": "00000000-1234-5678-1234-567812345678",
        "author_uuid": "10000000-1234-5678-1234-567812345678",
        "text": "comment 1",
    }
    assert second.operation_name == "store_comment_view"
    assert json.loads(second.data) == {
        "comment_uuid": "00000000-1234-5678-1234-567812345678",
        "viewer_uuid": "20000000-1234-5678-1234-567812345678",
    }

