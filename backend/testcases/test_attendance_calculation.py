import pytest
from datetime import datetime, timezone, timedelta
from app.attendance_service.service import _calc_working_hours
from app.attendance_service.models import AttendanceStatus


def calculate_status(diff_seconds: float) -> AttendanceStatus:
    """Mirrors the attendance shift status logic in check_out."""
    if diff_seconds >= 8.0 * 3600:
        return AttendanceStatus.PRESENT
    elif diff_seconds >= 4.0 * 3600:
        return AttendanceStatus.HALF_DAY
    else:
        return AttendanceStatus.PRESENT


def test_attendance_case_1():
    # CASE 1: Login 09:00, Logout 09:05 -> Working Hours = 00h 05m, Status != HALF_DAY
    login_time = datetime(2026, 9, 26, 9, 0, 0, tzinfo=timezone.utc)
    logout_time = datetime(2026, 9, 26, 9, 5, 0, tzinfo=timezone.utc)
    wh_str, wh_dec = _calc_working_hours(login_time, logout_time)
    diff_sec = (logout_time - login_time).total_seconds()
    status = calculate_status(diff_sec)

    assert wh_str == "00h 05m"
    assert status != AttendanceStatus.HALF_DAY
    assert status == AttendanceStatus.PRESENT


def test_attendance_case_2():
    # CASE 2: Login 09:00, Logout 12:59 -> Working Hours = 03h 59m, Status != HALF_DAY
    login_time = datetime(2026, 9, 26, 9, 0, 0, tzinfo=timezone.utc)
    logout_time = datetime(2026, 9, 26, 12, 59, 0, tzinfo=timezone.utc)
    wh_str, wh_dec = _calc_working_hours(login_time, logout_time)
    diff_sec = (logout_time - login_time).total_seconds()
    status = calculate_status(diff_sec)

    assert wh_str == "03h 59m"
    assert status != AttendanceStatus.HALF_DAY
    assert status == AttendanceStatus.PRESENT


def test_attendance_case_3():
    # CASE 3: Login 09:00, Logout 13:00 -> Working Hours = 04h 00m, Status = HALF_DAY
    login_time = datetime(2026, 9, 26, 9, 0, 0, tzinfo=timezone.utc)
    logout_time = datetime(2026, 9, 26, 13, 0, 0, tzinfo=timezone.utc)
    wh_str, wh_dec = _calc_working_hours(login_time, logout_time)
    diff_sec = (logout_time - login_time).total_seconds()
    status = calculate_status(diff_sec)

    assert wh_str == "04h 00m"
    assert status == AttendanceStatus.HALF_DAY


def test_attendance_case_4():
    # CASE 4: Login 09:00, Logout 16:59 -> Working Hours = 07h 59m, Status = HALF_DAY
    login_time = datetime(2026, 9, 26, 9, 0, 0, tzinfo=timezone.utc)
    logout_time = datetime(2026, 9, 26, 16, 59, 0, tzinfo=timezone.utc)
    wh_str, wh_dec = _calc_working_hours(login_time, logout_time)
    diff_sec = (logout_time - login_time).total_seconds()
    status = calculate_status(diff_sec)

    assert wh_str == "07h 59m"
    assert status == AttendanceStatus.HALF_DAY


def test_attendance_case_5():
    # CASE 5: Login 09:00, Logout 17:00 -> Working Hours = 08h 00m, Status = FULL_DAY (PRESENT)
    login_time = datetime(2026, 9, 26, 9, 0, 0, tzinfo=timezone.utc)
    logout_time = datetime(2026, 9, 26, 17, 0, 0, tzinfo=timezone.utc)
    wh_str, wh_dec = _calc_working_hours(login_time, logout_time)
    diff_sec = (logout_time - login_time).total_seconds()
    status = calculate_status(diff_sec)

    assert wh_str == "08h 00m"
    assert status == AttendanceStatus.PRESENT


def test_attendance_case_6():
    # CASE 6: Login 09:00, Logout 18:00 -> Working Hours = 09h 00m, Status = FULL_DAY (PRESENT)
    login_time = datetime(2026, 9, 26, 9, 0, 0, tzinfo=timezone.utc)
    logout_time = datetime(2026, 9, 26, 18, 0, 0, tzinfo=timezone.utc)
    wh_str, wh_dec = _calc_working_hours(login_time, logout_time)
    diff_sec = (logout_time - login_time).total_seconds()
    status = calculate_status(diff_sec)

    assert wh_str == "09h 00m"
    assert status == AttendanceStatus.PRESENT
