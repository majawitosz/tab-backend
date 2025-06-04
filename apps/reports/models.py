from django.db import models

class Report(models.Model):
    FILTER_CHOICES = [
        ('overall_income', 'Overall income'),
        ('dish_popularity', 'Dish popularity'),
        ('dish_income', 'Dish income'),
    ]

    title = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    filter_by = models.CharField(max_length=20, choices=FILTER_CHOICES)
    generated_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(blank=True)
    file = models.FileField(upload_to='reports/')

    def __str__(self):
        return f"{self.title} – {self.generated_at:%Y-%m-%d %H:%M}"