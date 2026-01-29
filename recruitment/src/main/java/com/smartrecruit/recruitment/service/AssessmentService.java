package com.smartrecruit.recruitment.service;

import com.smartrecruit.recruitment.entity.Assessment;
import com.smartrecruit.recruitment.entity.Candidate;
import com.smartrecruit.recruitment.enums.CandidateStatus;
import com.smartrecruit.recruitment.exception.CandidateNotFoundException;
import com.smartrecruit.recruitment.repository.AssessmentRepository;
import com.smartrecruit.recruitment.repository.CandidateRepository;
import org.springframework.stereotype.Service;

@Service
public class AssessmentService {

    private final AssessmentRepository assessmentRepository;
    private final CandidateRepository candidateRepository;

    public AssessmentService(AssessmentRepository assessmentRepository,
                             CandidateRepository candidateRepository) {
        this.assessmentRepository = assessmentRepository;
        this.candidateRepository = candidateRepository;
    }

    public Assessment assessCandidate(Long candidateId,
                                      int technicalScore,
                                      int communicationScore) {

        Candidate candidate = candidateRepository.findById(candidateId)
                .orElseThrow(() -> new CandidateNotFoundException(
                        "Candidate not found with id: " + candidateId));

        // BUSINESS RULE
        if (candidate.getStatus() != CandidateStatus.INTERVIEWED) {
            throw new RuntimeException("Only INTERVIEWED candidates can be assessed");
        }

        Assessment assessment = new Assessment();
        assessment.setCandidate(candidate);
        assessment.setTechnicalScore(technicalScore);
        assessment.setCommunicationScore(communicationScore);
        assessment.setOverallScore(calculateOverall(technicalScore, communicationScore));

        return assessmentRepository.save(assessment);
    }

    private double calculateOverall(int tech, int comm) {
        return (tech * 0.7) + (comm * 0.3);
    }
    public String autoDecide(Long candidateId) {

        Assessment assessment = assessmentRepository.findByCandidateId(candidateId)
                .orElseThrow(() -> new RuntimeException("Assessment not found"));

        Candidate candidate = assessment.getCandidate();

        if (candidate.getStatus() != CandidateStatus.INTERVIEWED) {
            throw new RuntimeException("Candidate must be INTERVIEWED for decision");
        }

        if (assessment.getOverallScore() >= 75) {
            candidate.setStatus(CandidateStatus.OFFERED);
            candidateRepository.save(candidate);
            return "OFFERED";
        } else {
            candidate.setStatus(CandidateStatus.REJECTED);
            candidateRepository.save(candidate);
            return "REJECTED";
        }
    }

}
