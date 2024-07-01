class NoMigrationRouter:
    """Router that prevents running migrations under any circumstances."""
    def allow_migration(self, *args, **kwargs):
        return False
