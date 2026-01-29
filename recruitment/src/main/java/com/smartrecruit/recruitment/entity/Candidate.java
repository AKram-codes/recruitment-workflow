package com.smartrecruit.recruitment.entity;

import com.smartrecruit.recruitment.enums.CandidateStatus;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Table(name = "candidates")
@Getter
@Setter
public class Candidate {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String fullName;
    private String email;
    private String phone;
    private int experienceYears;

    @Enumerated(EnumType.STRING)
    private CandidateStatus status;

    private LocalDateTime createdAt;
}
