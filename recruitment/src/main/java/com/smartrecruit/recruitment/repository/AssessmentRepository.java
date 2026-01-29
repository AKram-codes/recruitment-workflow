package com.smartrecruit.recruitment.repository;

import com.smartrecruit.recruitment.entity.Assessment;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;



public interface AssessmentRepository extends JpaRepository<Assessment, Long> {
    Optional<Assessment> findByCandidateId(Long candidateId);
}
