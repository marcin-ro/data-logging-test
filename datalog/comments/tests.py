import json
import pytest
import uuid

from .actions import CommentActions
from .models import Comment, CommentView, DataLog


def test_operations(db):
    # create a comment
    CommentActions.create_comment(
        target_uuid="00000000-1234-5678-1234-567812345678",
        author_uuid="10000000-1234-5678-1234-567812345678",
        text="comment 1",
    )
    assert Comment.objects.count() == 1
    comment = Comment.objects.latest()
    assert str(comment.target_uuid) == "00000000-1234-5678-1234-567812345678"
    assert comment.text == "comment 1"

    # view it
    CommentActions.store_comment_view(
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

