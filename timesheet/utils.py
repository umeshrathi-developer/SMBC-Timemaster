"""Utility functions for timesheet and holiday import"""
from openpyxl import load_workbook
from datetime import datetime
from decimal import Decimal
from django.core.exceptions import ValidationError
import logging
from .models import TimesheetSummary, TimesheetDetails, AttendanceSummary, AttendanceDetails, Holiday

import_logger = logging.getLogger('timesheet.import')


def import_holiday_file(file_obj):
    """
    Import holiday data from an Excel file.

    Expected columns:
    - S. No.
    - Date
    - Day
    - Holiday
    - Applicability

    Column mapping:
    - Holiday -> Holiday.name
    - Applicability -> Holiday.location
    - holiday_type -> PUBLIC_HOLIDAY
    """
    try:
        workbook = load_workbook(file_obj)
        worksheet = workbook.active
        results = {
            'success': True,
            'message': 'Holiday import completed successfully',
            'created_count': 0,
            'updated_count': 0,
            'errors': [],
        }

        header_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
        if not header_row:
            return {
                'success': False,
                'message': 'The uploaded file is empty.',
                'errors': ['Missing header row.'],
            }

        header_map = {
            str(column).strip().lower(): index
            for index, column in enumerate(header_row)
            if column is not None
        }
        required_headers = ['date', 'holiday', 'applicability']
        missing_headers = [header for header in required_headers if header not in header_map]
        if missing_headers:
            return {
                'success': False,
                'message': 'Missing required columns in holiday import file.',
                'errors': [f"Missing columns: {', '.join(missing_headers)}"],
            }

        for row_idx, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not row[header_map['date']] or not row[header_map['holiday']]:
                continue

            try:
                date_value = row[header_map['date']]
                if isinstance(date_value, datetime):
                    holiday_date = date_value.date()
                elif hasattr(date_value, 'year') and hasattr(date_value, 'month') and hasattr(date_value, 'day'):
                    holiday_date = date_value
                else:
                    holiday_date = datetime.strptime(str(date_value).strip(), '%Y-%m-%d').date()

                holiday_name = str(row[header_map['holiday']]).strip()
                location = str(row[header_map['applicability']]).strip() if row[header_map['applicability']] else ''

                holiday, created = Holiday.objects.update_or_create(
                    date=holiday_date,
                    name=holiday_name,
                    location=location,
                    defaults={
                        'holiday_type': 'PUBLIC_HOLIDAY',
                    }
                )

                if created:
                    results['created_count'] += 1
                else:
                    results['updated_count'] += 1
            except Exception as exc:
                results['errors'].append(f'Row {row_idx}: {str(exc)}')

        workbook.close()

        if results['errors']:
            results['success'] = False
            results['message'] = f"Holiday import completed with {len(results['errors'])} errors"

        return results
    except Exception as exc:
        import_logger.error(f"Failed to import holiday file: {str(exc)}", exc_info=True)
        return {
            'success': False,
            'message': f'Failed to import holiday file: {str(exc)}',
            'errors': [str(exc)],
        }


def import_timesheet_file(file_path, import_date=None):
    """
    Import timesheet data from XLSX file using bulk_create for performance optimization.
    Expected sheets: Timesheet Summary, Timesheet Details, Attendance Summary, Attendance Details
    
    Uses bulk_create() for batch insert operations to reduce database I/O calls significantly.
    Batch size of 1000 records per insert to balance memory usage and performance.
    
    Args:
        file_path: Path to the XLSX file
        import_date: Date/Month of the import (optional, for filtering later)
    """
    import_logger.info(f"Starting timesheet import from file: {file_path}, import_date: {import_date}")
    
    try:
        workbook = load_workbook(file_path)
        results = {
            'success': True,
            'message': 'Import completed successfully',
            'summary_count': 0,
            'details_count': 0,
            'attendance_summary_count': 0,
            'attendance_details_count': 0,
            'errors': []
        }
        
        import_logger.info(f"Excel file loaded. Sheets found: {workbook.sheetnames}")
        BATCH_SIZE = 1000  # Process records in batches of 1000

        # Import Timesheet Summary
        if 'Timesheet Summary' in workbook.sheetnames:
            try:
                ws = workbook['Timesheet Summary']
                summaries_to_create = []
                
                for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
                    if row_idx == 1:  # Skip header
                        continue
                    if not row[0]:  # Skip empty rows
                        continue
                    
                    try:
                        summary = TimesheetSummary(
                            email_id=str(row[0]).strip(),
                            team_member=str(row[1]).strip(),
                            project_id=int(row[2]),
                            project=str(row[3]).strip(),
                            total_hours=Decimal(str(row[4])),
                            import_date=import_date
                        )
                        summaries_to_create.append(summary)
                    except Exception as e:
                        results['errors'].append(f"Timesheet Summary Row {row_idx}: {str(e)}")
                
                # Bulk insert in batches
                if summaries_to_create:
                    TimesheetSummary.objects.bulk_create(summaries_to_create, batch_size=BATCH_SIZE)
                    results['summary_count'] = len(summaries_to_create)
                    import_logger.info(f"Bulk created {results['summary_count']} Timesheet Summary records")
                    
            except Exception as e:
                results['errors'].append(f"Error processing Timesheet Summary: {str(e)}")

        # Import Timesheet Details
        if 'Timesheet Details' in workbook.sheetnames:
            try:
                ws = workbook['Timesheet Details']
                details_to_create = []
                
                for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
                    if row_idx == 1:  # Skip header
                        continue
                    if not row[0]:  # Skip empty rows
                        continue
                    
                    try:
                        # Parse date
                        date_val = row[4]
                        if isinstance(date_val, datetime):
                            date_val = date_val.date()
                        else:
                            date_val = datetime.strptime(str(date_val), '%Y-%m-%d').date()
                        
                        detail = TimesheetDetails(
                            email_id=str(row[0]).strip(),
                            team_member=str(row[1]).strip(),
                            project_id=int(row[2]),
                            project=str(row[3]).strip(),
                            date=date_val,
                            time_logged=Decimal(str(row[5])),
                            comment=str(row[6]).strip() if row[6] else '',
                            import_date=import_date
                        )
                        details_to_create.append(detail)
                    except Exception as e:
                        results['errors'].append(f"Timesheet Details Row {row_idx}: {str(e)}")
                
                # Bulk insert in batches
                if details_to_create:
                    TimesheetDetails.objects.bulk_create(details_to_create, batch_size=BATCH_SIZE)
                    results['details_count'] = len(details_to_create)
                    import_logger.info(f"Bulk created {results['details_count']} Timesheet Details records")
                    
            except Exception as e:
                results['errors'].append(f"Error processing Timesheet Details: {str(e)}")

        # Import Attendance Summary
        if 'Attendance Summary' in workbook.sheetnames:
            try:
                ws = workbook['Attendance Summary']
                att_summaries_to_create = []
                
                for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
                    if row_idx == 1:  # Skip header
                        continue
                    if not row[0]:  # Skip empty rows
                        continue
                    
                    try:
                        summary = AttendanceSummary(
                            email_id=str(row[0]).strip(),
                            team_member=str(row[1]).strip(),
                            business_hours=Decimal(str(row[2])),
                            available_hours=Decimal(str(row[3])),
                            project_hours=Decimal(str(row[4])),
                            import_date=import_date
                        )
                        att_summaries_to_create.append(summary)
                    except Exception as e:
                        results['errors'].append(f"Attendance Summary Row {row_idx}: {str(e)}")
                
                # Bulk insert in batches
                if att_summaries_to_create:
                    AttendanceSummary.objects.bulk_create(att_summaries_to_create, batch_size=BATCH_SIZE)
                    results['attendance_summary_count'] = len(att_summaries_to_create)
                    import_logger.info(f"Bulk created {results['attendance_summary_count']} Attendance Summary records")
                    
            except Exception as e:
                results['errors'].append(f"Error processing Attendance Summary: {str(e)}")

        # Import Attendance Details
        if 'Attendance Details' in workbook.sheetnames:
            try:
                ws = workbook['Attendance Details']
                att_details_to_create = []
                
                for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
                    if row_idx == 1:  # Skip header
                        continue
                    if not row[0]:  # Skip empty rows
                        continue
                    
                    try:
                        # Parse date
                        date_val = row[2]
                        if isinstance(date_val, datetime):
                            date_val = date_val.date()
                        else:
                            date_val = datetime.strptime(str(date_val), '%Y-%m-%d').date()
                        
                        detail = AttendanceDetails(
                            email_id=str(row[0]).strip(),
                            team_member=str(row[1]).strip(),
                            date=date_val,
                            business_hours=Decimal(str(row[3])),
                            available_hours=Decimal(str(row[4])),
                            remarks=str(row[5]).strip() if row[5] else '',
                            import_date=import_date
                        )
                        att_details_to_create.append(detail)
                    except Exception as e:
                        results['errors'].append(f"Attendance Details Row {row_idx}: {str(e)}")
                
                # Bulk insert in batches
                if att_details_to_create:
                    AttendanceDetails.objects.bulk_create(att_details_to_create, batch_size=BATCH_SIZE)
                    results['attendance_details_count'] = len(att_details_to_create)
                    import_logger.info(f"Bulk created {results['attendance_details_count']} Attendance Details records")
                    
            except Exception as e:
                results['errors'].append(f"Error processing Attendance Details: {str(e)}")

        if results['errors']:
            results['success'] = False
            results['message'] = f"Import completed with {len(results['errors'])} errors"
            import_logger.warning(f"Import completed with {len(results['errors'])} errors: {results['errors']}")
        else:
            results['message'] = 'Import completed successfully'
            import_logger.info(f"Import completed successfully (using bulk_create). Summary={results['summary_count']}, Details={results['details_count']}, "
                              f"AttSummary={results['attendance_summary_count']}, AttDetails={results['attendance_details_count']}")
        
        workbook.close()
        return results

    except Exception as e:
        import_logger.error(f"Failed to import file: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f"Failed to import file: {str(e)}",
            'errors': [str(e)]
        }
