package com.smartrecruit.recruitment.repository;

import com.smartrecruit.recruitment.entity.Candidate;
import com.smartrecruit.recruitment.enums.CandidateStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface CandidateRepository extends JpaRepository<Candidate, Long> {

    List<Candidate> findByStatus(CandidateStatus status);
}
