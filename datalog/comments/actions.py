import functools
import uuid
from django.core.serializers.json import DjangoJSONEncoder
from django.db.transaction import atomic
from .models import Comment, CommentView, DataLog


def action(action_func):
    """A decorator that plugs action_func into the logging machinery.

    It's dead simple now.  It limits action_func to only accept kwargs to make
    all stored log entries consistent and annotated.  It requires that all the
    data for the writer func is passed explicitly, via simple objects
    serializable to JSON (with Django extensions to allow UUID).

    Ideally it would detect nested calls, so that e.g. create_comment below
    would call store_comment_view and have those actions add two separate
    entries, but connected into a higher-level changeset.

    This is likely to run in an external transaction, but the decorator also
    opens a new transaction to be safe.

    All the example operations below follow the convention that outside of
    actions models are read-only.  With some model tweaks we can probably
    effectively enforce that: only use models to read the data, use all the
    filtering niceties, but never use them directly to write to it, and
    strongly nudge developers in the direction of using actions.

    The writer functions do not see DataLog entries directly and would have to
    do extra work to get to them; we can probably work with Postgresql
    permissions to prevent that if we really want to, but it's probably not
    necessary.
    """

    @functools.wraps(action_func)
    def wrapper(**kwargs):
        with atomic():
            # We can get a hold of the log entry here and provide it to all
            # operations, return it, connect it to higher-level operations (we can
            # detect that this is a nested action).
            log = DataLog.objects.create(
                # We could also include the idea of adding an object's hash and
                # use it to prevent parallel operations on the same object, but
                # the calling code would be responsible of passing it here.
                operation_name=action_func.__name__,
                data=DjangoJSONEncoder().encode(kwargs),
            )
            return action_func(**kwargs)

    return wrapper


class CommentActions:
    """
    CommentActions contains all the actions registered in the comments app.

    It's just a quick sketch, so it still uses the @action decorator, but
    ideally this would either be a metaclass that augments all its methods
    automatically, or a registry built by registering functions defined
    elsewhere.
    """

    @staticmethod
    @action
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

    @staticmethod
    @action
    def edit_comment(comment_uuid: uuid.UUID, text: str):
        """Edit an existing comment.
        """
        rows_matched = Comment.objects.filter(uuid=comment_uuid).update(text=text)
        if rows_matched != 1:
            raise Exception("oh no")

    @staticmethod
    @action
    def delete_comment(comment_uuid: uuid.UUID):
        """Delete a comment.
        """
        rows_deleted = Comment.objects.filter(uuid=comment_uuid).delete()
        if rows_deleted != 1:
            raise Exception("oh no")

    @staticmethod
    @action
    def store_comment_view(
        comment_uuid: uuid.UUID, viewer_uuid: uuid.UUID
    ) -> CommentView:
        """Store the information that someone viewed a comment.
    
        (very ineffective, but this is for demonstration only)
        """
        return CommentView.objects.create(
            comment_uuid=comment_uuid, viewer_uuid=viewer_uuid
        )
