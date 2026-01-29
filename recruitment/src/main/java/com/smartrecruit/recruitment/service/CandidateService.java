package com.smartrecruit.recruitment.service;

import com.smartrecruit.recruitment.entity.Candidate;
import com.smartrecruit.recruitment.enums.CandidateStatus;
import com.smartrecruit.recruitment.repository.CandidateRepository;
import org.springframework.stereotype.Service;
import com.smartrecruit.recruitment.exception.CandidateNotFoundException;


import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class CandidateService {

    private final CandidateRepository repository;

    public CandidateService(CandidateRepository repository) {
        this.repository = repository;
    }

    public Candidate createCandidate(Candidate candidate) {
        candidate.setStatus(CandidateStatus.APPLIED);
        candidate.setCreatedAt(LocalDateTime.now());
        return repository.save(candidate);
    }

    public Candidate updateStatus(Long id, CandidateStatus newStatus) {
        Candidate candidate = repository.findById(id)
                .orElseThrow(() -> new CandidateNotFoundException("Candidate not found with id: " + id));

        validateTransition(candidate.getStatus(), newStatus);
        candidate.setStatus(newStatus);

        return repository.save(candidate);
    }

    private void validateTransition(CandidateStatus current, CandidateStatus next) {

        if (current == CandidateStatus.APPLIED &&
                (next == CandidateStatus.INTERVIEWED || next == CandidateStatus.REJECTED)) {
            return;
        }

        if (current == CandidateStatus.INTERVIEWED &&
                (next == CandidateStatus.OFFERED || next == CandidateStatus.REJECTED)) {
            return;
        }

        throw new RuntimeException("Invalid status transition");
    }

    public Map<CandidateStatus, Long> getPipelineStats() {
        return repository.findAll()
                .stream()
                .collect(
                        java.util.stream.Collectors.groupingBy(
                                Candidate::getStatus,
                                java.util.stream.Collectors.counting()
                        )
                );
    }
    public List<Candidate> interviewedCandidates() {
        return repository.findByStatus(CandidateStatus.INTERVIEWED);
    }


    public List<Candidate> getByStatus(CandidateStatus status) {
        return repository.findByStatus(status);
    }
}
