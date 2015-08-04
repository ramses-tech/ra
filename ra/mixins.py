from six.moves import urllib

from .raml_utils import (
    get_query_params,
    get_body_by_mediatype
)
from .utils import (
    retry,
    fill_required_params,
    RandomValueGenerator,
)
from .base import DEFAULT_MEDIA_TYPE


class ResourceRequestMixin(object):
    _request_func = None
    _request_body = None
    _request_schema = None
    _required_params = None

    def __init__(self, *args, **kwargs):
        self.testapp = kwargs.pop('testapp')
        super(ResourceRequestMixin, self).__init__(*args, **kwargs)

    @property
    def base_url(self):
        return self.resource.absolute_uri

    @property
    def request(self, *args, **kwargs):
        if self._request_func is None:
            http_method = self.resource.method.lower()
            self._request_func = getattr(
                self, '_{}_request'.format(http_method))
        return self._request_func

    @property
    def request_body(self, *args, **kwargs):
        if self._request_body is None:
            media_type = DEFAULT_MEDIA_TYPE
            body = get_body_by_mediatype(self.resource, media_type)
            self._request_body = None if body is None else body.example
        return self._request_body

    @property
    def request_schema(self, *args, **kwargs):
        if self._request_schema is None:
            media_type = DEFAULT_MEDIA_TYPE
            body = get_body_by_mediatype(self.resource, media_type)
            self._request_schema = None if body is None else body.schema
        return self._request_schema

    @property
    def required_params(self):
        if self._required_params is None:
            raml_params = get_query_params(
                self.resource, required_only=True)
            self._required_params = {
                param.name: RandomValueGenerator.generate_value(
                    param.raw)
                for param in raml_params}
        return self._required_params

    def make_url(self, params=None, base_url=None, add_required=True):
        if base_url is None:
            base_url = self.base_url
        if params is None:
            params = {}
        if add_required:
            params.update(self.required_params)

        if params:
            # http://stackoverflow.com/a/2506477
            url_parts = list(urllib.parse.urlparse(base_url))
            query = dict(urllib.parse.parse_qsl(url_parts[4]))
            query.update(params)
            url_parts[4] = urllib.parse.urlencode(query)
            return urllib.parse.urlunparse(url_parts)

        return base_url

    def _get_request(self, url=None, **kwargs):
        if url is None:
            url = self.make_url()
        return retry(self.testapp.get, args=(url,), kwargs=kwargs)

    def _head_request(self, url=None, **kwargs):
        if url is None:
            url = self.make_url()
        return retry(self.testapp.head, args=(url,), kwargs=kwargs)

    def _options_request(self, url=None, **kwargs):
        if url is None:
            url = self.make_url()
        return retry(self.testapp.options, args=(url,), kwargs=kwargs)

    def _create_update_request(self, url, method, **kwargs):
        if url is None:
            url = self.make_url()
        request_body = self.request_body or {}

        # Fill request body example with required fields from request
        # body schema.
        if self.request_schema is not None:
            request_body = fill_required_params(
                request_body, self.request_schema)

        meth = getattr(self.testapp, '{}_json'.format(method))
        kwargs['params'] = request_body
        return retry(meth, args=(url,), kwargs=kwargs)

    def _post_request(self, url=None, **kwargs):
        return self._create_update_request(url, 'post', **kwargs)

    def _patch_request(self, url=None, **kwargs):
        return self._create_update_request(url, 'patch', **kwargs)

    def _put_request(self, url=None, **kwargs):
        return self._create_update_request(url, 'put', **kwargs)

    def _delete_request(self, url=None, **kwargs):
        return self._create_update_request(url, 'delete', **kwargs)
