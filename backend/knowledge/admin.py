from django.contrib import admin

from knowledge.models import QueryLog


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'question', 'row_count')
    search_fields = ('question', 'cypher')
    list_filter = ('created_at',)
