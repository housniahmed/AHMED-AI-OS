CREATE FUNCTION enforce_approval_transition() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='INSERT' THEN
  IF NEW.state <> 'pending' OR NEW.approver_id IS NOT NULL OR NEW.claimed_at IS NOT NULL OR NEW.finished_at IS NOT NULL OR NEW.receipt IS NOT NULL THEN
   RAISE EXCEPTION 'invalid initial approval state';
  END IF;
  RETURN NEW;
 END IF;
 IF OLD.state='pending' AND NEW.state IN ('approved','rejected') THEN
  IF OLD.expires_at<=clock_timestamp() OR NEW.approver_id IS DISTINCT FROM OLD.owner_id OR
     (NEW.state='approved' AND ((OLD.payload->>'risk')::int IS NULL OR (OLD.payload->>'risk')::int NOT BETWEEN 1 AND 3))
     OR NEW.claimed_at IS DISTINCT FROM OLD.claimed_at OR NEW.finished_at IS DISTINCT FROM OLD.finished_at OR NEW.receipt IS DISTINCT FROM OLD.receipt THEN
   RAISE EXCEPTION 'invalid approval decision';
  END IF;
 ELSIF OLD.state='approved' AND NEW.state='executing' THEN
  IF OLD.expires_at<=clock_timestamp() OR NEW.claimed_at IS NULL OR NEW.approver_id IS DISTINCT FROM OLD.approver_id OR NEW.finished_at IS DISTINCT FROM OLD.finished_at OR NEW.receipt IS DISTINCT FROM OLD.receipt THEN
   RAISE EXCEPTION 'invalid approval claim';
  END IF;
 ELSIF OLD.state='executing' AND NEW.state IN ('succeeded','uncertain') THEN
  IF NEW.finished_at IS NULL OR NEW.finished_at<OLD.claimed_at OR NEW.approver_id IS DISTINCT FROM OLD.approver_id OR NEW.claimed_at IS DISTINCT FROM OLD.claimed_at THEN
   RAISE EXCEPTION 'invalid approval finish';
  END IF;
 ELSE
  RAISE EXCEPTION 'invalid approval transition';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER approval_transition BEFORE INSERT OR UPDATE ON approval_ledger
FOR EACH ROW EXECUTE FUNCTION enforce_approval_transition();
