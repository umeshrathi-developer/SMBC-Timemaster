# Comp-Off Validation & Form Fixes

## Issues Fixed (Version 2)

### 1. ✅ Working Date Validation
**Issue**: No validation preventing working_date from being after compoff_date

**Solution**: Added cross-field validation in `CompOffForm.clean()`
```python
def clean(self):
    cleaned_data = super().clean()
    working_date = cleaned_data.get('working_date')
    compoff_date = cleaned_data.get('compoff_date')
    
    if working_date and compoff_date:
        if working_date < compoff_date:
            raise forms.ValidationError(
                'Working date must be before or equal to Comp-Off date.'
            )
    return cleaned_data
```

**Error Message**: "Working date must be before or equal to Comp-Off date."

**How It Works**:
- Employee works on a weekend/holiday (working_date)
- Employee takes Comp-Off on a future weekday (compoff_date)
- Working date must be <= Comp-Off date

**Example**:
- ❌ Working date: 2024-04-15, Comp-Off date: 2024-04-10 (INVALID - working is in future)
- ✅ Working date: 2024-04-10, Comp-Off date: 2024-04-15 (VALID - working is before compoff)

### 2. ✅ Employee Dropdown Shows All Employees
**Issue**: When form validation failed on POST request, employee dropdown showed all employees instead of just active ones

**Root Cause**: The employee field queryset was only being filtered in GET requests, not on form reload after validation errors

**Solution**: 
1. Added `__init__` method to `CompOffForm` to always ensure queryset filters for active employees:
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Always ensure employee field shows only active employees
    self.fields['employee'].queryset = Employee.objects.filter(is_active=True)
```

2. Updated `compoff_add` view to apply custom filtering even on validation errors:
```python
if request.method == 'POST':
    form = CompOffForm(request.POST)
    if form.is_valid():
        # ... save logic
    else:
        # For non-admin users with validation errors, restrict dropdown
        if not is_admin(request.user):
            form.fields['employee'].queryset = Employee.objects.filter(id=employee.id)
```

3. Applied same fix to `compoff_edit` view for consistency

**Result**: 
- ✅ Admins always see all active employees
- ✅ Employees always see only their own employee record
- ✅ On form reload after errors, dropdown stays consistent

## Validation Summary

### Comp-Off Date Validations

| Validation | Rule | Error Message |
|---|---|---|
| **Working Date** | Must be weekend or public holiday (not SPECIAL_HOLIDAY) | "Working date must be a weekend (Saturday/Sunday) or a public holiday." |
| **Comp-Off Date** | Must be weekday (Mon-Fri) AND not a holiday | "Comp-Off date must be a weekday (Monday to Friday)." / "Comp-Off date cannot be a holiday or weekend." |
| **Date Relationship** | Working Date <= Comp-Off Date | "Working date must be before or equal to Comp-Off date." |
| **Employee** | Must be active employee | Dropdown filtered to active employees only |
| **Status** | PENDING or TAKEN | Form selection dropdown |

## Testing Scenarios

### Test Case 1: Invalid Date Relationship
1. Open Add Comp-Off form
2. Select Employee: Any Active Employee
3. Working Date: 2024-04-20 (Friday)
4. Comp-Off Date: 2024-04-15 (Monday - before working date)
5. Click Save
6. **Expected**: Error message "Working date must be before or equal to Comp-Off date."

### Test Case 2: Inactive Employee Doesn't Appear
1. Deactivate an employee in Employee Management
2. Open Add Comp-Off form
3. Click on Employee dropdown
4. **Expected**: Deactivated employee NOT in the dropdown list

### Test Case 3: Form Validation Error Reloads Correctly
1. Fill form with invalid dates
2. Submit form
3. Validation error appears
4. **Expected**: 
   - Error message displayed clearly
   - Employee dropdown shows only active employees (admin) or only your employee (non-admin)
   - Form data is preserved for correction

### Test Case 4: Non-Admin Can Only Select Own Employee
1. Login as regular employee
2. Open Add Comp-Off form
3. Check Employee dropdown
4. **Expected**: Only their own employee name appears (no other employees)
5. Check Edit Comp-Off for same employee
6. **Expected**: Employee field is disabled

## Benefits

✅ **Better Data Integrity**: Working dates must logically precede or match Comp-Off dates
✅ **Better UX**: Dropdown always shows correct filtered list even after validation errors
✅ **Security**: Employees can only see/select their own record for CompOff
✅ **Consistency**: Both add and edit views handle filtering the same way
✅ **Clear Error Messages**: Users understand what's wrong and why

## Files Modified

1. **timesheet/forms.py**:
   - Added `__init__` method to CompOffForm
   - Added `clean()` method for cross-field validation

2. **timesheet/views.py**:
   - Updated `compoff_add()` - handle form errors with proper filtering
   - Updated `compoff_edit()` - handle form errors with proper filtering

3. **templates/timesheet/compoff_form.html**: (No changes - already supports non_field_errors)
