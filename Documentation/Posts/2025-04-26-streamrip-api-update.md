# 2025-04-26: StreamRip API Update

After finding the StreamRip v2 scripting documentation, I realized we were using an incorrect import pattern in our downloader script. The original implementation was using:

```python
from streamrip.api import rip, RipStatus, RipResult
```

But according to the [official documentation](https://github.com/nathom/streamrip/wiki/Scripting-with-Streamrip-v2), the correct approach is:

```python
from streamrip import Stream, RipStatus
```

The API usage is also different. Instead of calling a `rip()` function directly, we need to:
1. Create a `Stream` object with our search parameters
2. Call the `download()` method on that object

This is how we updated the code:

```python
# Before:
result: RipResult = rip(
    query=search_query,
    source=PREFERRED_SOURCE,
    output_path=OUTPUT_DIR,
    skip_existing=True,
)

# After:
stream = Stream(
    query=search_query,
    source=PREFERRED_SOURCE,
    output_dir=str(OUTPUT_DIR),
    skip_existing=True,
)
result = stream.download()
```

There was also a parameter name change from `output_path` to `output_dir` according to the documentation.

This update should make our script more compatible with the intended StreamRip v2 API usage pattern. The objects and methods might have slightly different behaviors and return values than we originally expected, so we'll need to test this updated approach to ensure it works as expected.
