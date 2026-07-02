"""Management command to generate Accrual records from existing CompOff data."""

from django.core.management.base import BaseCommand

from timesheet.models import Accrual, CompOff


class Command(BaseCommand):
    help = 'Generate Accrual records from existing CompOff records (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be created without saving any Accrual rows.',
        )
        parser.add_argument(
            '--status',
            choices=['PENDING', 'TAKEN', 'ALL'],
            default='ALL',
            help='Limit the migration to a specific CompOff status.',
        )

    def handle(self, *args, **options):
        queryset = CompOff.objects.select_related('employee').order_by('employee__employee_id', 'working_date', 'compoff_date')

        if options['status'] != 'ALL':
            queryset = queryset.filter(status=options['status'])

        created_count = 0
        skipped_count = 0

        for compoff in queryset:
            status = 'ADJUSTED' if compoff.compoff_date else 'PENDING'

            existing_accrual = Accrual.objects.filter(
                employee=compoff.employee,
                working_date=compoff.working_date,
                adjusted_date=compoff.compoff_date,
                status=status,
            ).exists()

            if existing_accrual:
                skipped_count += 1
                continue

            notes = compoff.notes.strip() if compoff.notes else ''
            details = f"Generated from existing CompOff #{compoff.pk}."
            accrual_notes = ' '.join(filter(None, [details, notes]))

            accrual = Accrual(
                employee=compoff.employee,
                working_date=compoff.working_date,
                adjusted_date=compoff.compoff_date,
                status=status,
                notes=accrual_notes,
            )

            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING(
                        f"[dry-run] Would create Accrual for {compoff.employee.name} on "
                        f"{compoff.working_date or 'N/A'}"
                    )
                )
                created_count += 1
                continue

            accrual.save()
            created_count += 1

        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Dry-run complete: {created_count} Accrual(s) would be created; '
                    f'{skipped_count} already exist.'
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Generated {created_count} Accrual(s) from existing CompOff records; '
                f'{skipped_count} Accrual(s) were already present.'
            )
        )
