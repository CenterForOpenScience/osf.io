"""Tests for failure loading callback
"""

from stevedore import extension


def test_extension_failure_custom_callback():
    errors = []

    def failure_callback(manager, entrypoint, error):
        errors.append((manager, entrypoint, error))

    em = extension.ExtensionManager('stevedore.test.extension',
                                    invoke_on_load=True,
                                    on_load_failure_callback=failure_callback)
    extensions = list(em.extensions)
    assert len(extensions) > 0
    assert len(errors) == 1
    (manager, entrypoint, error) = errors[0]
    assert manager is em
    assert isinstance(error, IOError)
