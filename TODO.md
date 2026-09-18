# Fix Members/Trainer Loading Issue - TODO

## Plan Steps (Approved by User)
**Status Legend**: ⏳ Pending | ✅ Complete | ❌ Blocked

### 1. [✅ Complete] Create TODO.md for tracking
### 2. ⏳ Edit frontend/js/script.js\n   - Undo previous changes per user request\n   - Will propose simpler fix: add credentials only to loadMembers/loadTrainers fetches
   - Add `credentials: 'include'` to ALL fetch calls (login, members, trainers, payments, workouts, etc.)
   - Add global fetch wrapper with auth error handling (401/403 → clear storage + redirect login)
   - Improve loadMembers/loadTrainers error display

### 3. ⏳ Test changes
   - Login as admin/trainer
   - Visit members.html → verify table loads
   - Visit trainers.html → verify table loads
   - Check browser console for errors

### 4. ⏳ Verify/seed data
   - Run `python backend/test_tables.py`
   - Check MySQL: `SELECT COUNT(*) FROM members;` and `FROM trainers;`
   - Manual inserts if empty

### 5. ⏳ Final verification & completion

**Next**: Edit script.js then test.

