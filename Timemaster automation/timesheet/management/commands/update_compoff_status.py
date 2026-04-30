"""Management command to update Comp-Off status based on compoff_date"""
from datetime import date
from django.core.management.base import BaseCommand
from django.db.models import F, Q
from timesheet.models import CompOff


class Command(BaseCommand):
    help = 'Update Comp-Off status based on compoff_date (past dates become TAKEN, empty dates become PENDING)'

    def handle(self, *args, **options):
        updated_count = 0
        
        # Update CompOffs with past dates to TAKEN
        past_compoffs = CompOff.objects.filter(
            compoff_date__lt=date.today()
        ).filter(
            Q(working_date__isnull=True) | Q(working_date__lte=F('compoff_date'))
        ).exclude(status='TAKEN')
        
        past_count = past_compoffs.count()
        if past_count > 0:
            past_compoffs.update(status='TAKEN')
            updated_count += past_count
            self.stdout.write(
                self.style.SUCCESS(f'✓ Updated {past_count} CompOff(s) with past dates to TAKEN status')
            )
        
        # Update CompOffs with empty dates to PENDING
        empty_date_compoffs = CompOff.objects.filter(
            compoff_date__isnull=True
        ).exclude(status='PENDING')
        
        empty_count = empty_date_compoffs.count()
        if empty_count > 0:
            empty_date_compoffs.update(status='PENDING')
            updated_count += empty_count
            self.stdout.write(
                self.style.SUCCESS(f'✓ Updated {empty_count} CompOff(s) with empty dates to PENDING status')
            )
        
        if updated_count == 0:
            self.stdout.write(
                self.style.WARNING('ℹ No Comp-Off records needed status updates')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Total {updated_count} Comp-Off record(s) updated successfully!')
            )
