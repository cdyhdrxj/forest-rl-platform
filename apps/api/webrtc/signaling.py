from fastapi import APIRouter, Request
from handlers import httphandler

router = APIRouter()

router.get('/connection')(httphandler.get_connection)
router.get('/offer')(httphandler.get_offer)
router.get('/answer')(httphandler.get_answer)
router.get('/candidate')(httphandler.get_candidate)
router.get('')(httphandler.get_all)
router.put('')(httphandler.create_session)
router.delete('')(httphandler.delete_session)
router.put('/connection')(httphandler.create_connection)
router.delete('/connection')(httphandler.delete_connection)
router.post('/offer')(httphandler.post_offer)
router.post('/answer')(httphandler.post_answer)
router.post('/candidate')(httphandler.post_candidate)